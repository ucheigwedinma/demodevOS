"""
Feature flag resolution service.

Provides functions to check if a flag is enabled for a given context.
"""


from apps.accounts.models import Organization

# Tier ordering for comparison
TIER_ORDER = {"essentials": 0, "growth": 1, "scale": 2, "custom": 3}


def is_flag_enabled(
    flag_key: str,
    organization: Organization,
    project_id: int | None = None,
    region: str | None = None,
) -> bool:
    """
    Resolve whether a feature flag is enabled for the given context.

    Resolution order:
    1. If flag definition is not active (kill switch) → False
    2. If org's tier is below flag's minimum_tier → False
    3. If a FeatureFlagOverride exists for this org:
       a. If override.enabled is False → False
       b. If flag scope is 'project' and scoped_project_ids is non-empty:
          return project_id in scoped_project_ids
       c. If flag scope is 'region' and scoped_regions is non-empty:
          return region in scoped_regions
       d. Otherwise → override.enabled
    4. Fall back to flag.default_enabled
    """
    from .models import FeatureFlagDefinition, FeatureFlagOverride

    try:
        flag = FeatureFlagDefinition.objects.get(key=flag_key, is_active=True)
    except FeatureFlagDefinition.DoesNotExist:
        return False

    # Tier check
    org_tier_level = TIER_ORDER.get(organization.subscription_tier, 0)
    flag_tier_level = TIER_ORDER.get(flag.minimum_tier, 0)
    if org_tier_level < flag_tier_level:
        return False

    # Check for override
    try:
        override = FeatureFlagOverride.objects.get(
            flag=flag, organization=organization
        )
    except FeatureFlagOverride.DoesNotExist:
        return flag.default_enabled

    if not override.enabled:
        return False

    # Project scoping
    if flag.scope == FeatureFlagDefinition.FlagScope.PROJECT:
        if override.scoped_project_ids and project_id is not None:
            return project_id in override.scoped_project_ids

    # Region scoping
    if flag.scope == FeatureFlagDefinition.FlagScope.REGION:
        if override.scoped_regions and region is not None:
            return region.upper() in [r.upper() for r in override.scoped_regions]

    return override.enabled


def get_org_flags(organization: Organization) -> dict[str, bool]:
    """
    Return a dict of {flag_key: enabled} for all active flags for this org.
    Used by the frontend to get the full flag state in one call.
    """
    from .models import FeatureFlagDefinition, FeatureFlagOverride

    flags = FeatureFlagDefinition.objects.filter(is_active=True)
    overrides = {
        o.flag_id: o
        for o in FeatureFlagOverride.objects.filter(
            organization=organization,
            flag__is_active=True,
        ).select_related("flag")
    }

    org_tier_level = TIER_ORDER.get(organization.subscription_tier, 0)
    result = {}

    for flag in flags:
        flag_tier_level = TIER_ORDER.get(flag.minimum_tier, 0)
        if org_tier_level < flag_tier_level:
            result[flag.key] = False
            continue

        override = overrides.get(flag.id)
        if override:
            result[flag.key] = override.enabled
        else:
            result[flag.key] = flag.default_enabled

    return result
