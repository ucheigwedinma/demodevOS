from __future__ import annotations

from decimal import Decimal

from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.finance.models import JournalEntry, JournalSourceType
from apps.properties.asset_workflows import (
    amc_status_for,
    current_book_value_for,
    maintenance_status_for,
    monthly_depreciation_for,
    sync_asset_depreciation_journal,
    warranty_status_for,
)
from apps.properties.models import AssetComponent
from apps.properties.serializers import (
    AssetComponentDetailSerializer,
    AssetComponentListSerializer,
    AssetComponentWriteSerializer,
)
from apps.settings.permissions import HasRolePermission


def _resolve_user_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _money(value: Decimal | None) -> str:
    raw = value or Decimal("0.00")
    return f"{raw:.2f}"


def _asset_location_label(asset: AssetComponent) -> str:
    if asset.facility_space_id:
        if asset.facility_space.space_label:
            return asset.facility_space.space_label
        if asset.facility_space.unit_id:
            return asset.facility_space.unit.unit_number
    if asset.location_description:
        return asset.location_description
    if asset.unit_id:
        return asset.unit.unit_number
    return ""


def _asset_watch_row(asset: AssetComponent) -> dict[str, object]:
    return {
        "id": asset.id,
        "component_id": asset.component_id,
        "name": asset.name,
        "property_name": asset.property.name if asset.property_id else "",
        "facility_code": asset.facility.facility_code if asset.facility_id else "",
        "location_label": _asset_location_label(asset),
        "vendor_name": asset.vendor.name if asset.vendor_id else "",
        "amc_vendor_name": asset.amc_vendor.name if asset.amc_vendor_id else "",
        "maintenance_next_due_date": asset.maintenance_next_due_date.isoformat() if asset.maintenance_next_due_date else None,
        "warranty_expiry": asset.warranty_expiry.isoformat() if asset.warranty_expiry else None,
        "amc_end_date": asset.amc_end_date.isoformat() if asset.amc_end_date else None,
        "lifecycle_stage": asset.lifecycle_stage,
        "condition_rating": asset.condition_rating,
        "iot_status": asset.iot_status,
        "iot_last_seen_at": asset.iot_last_seen_at.isoformat() if asset.iot_last_seen_at else None,
        "monthly_depreciation": _money(monthly_depreciation_for(asset)),
        "current_book_value": _money(current_book_value_for(asset)),
        "warranty_status": warranty_status_for(asset),
        "amc_status": amc_status_for(asset),
        "maintenance_status": maintenance_status_for(asset),
    }


class FacilityAssetOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        today = timezone.localdate()
        period_token = today.strftime("%Y%m")
        assets = list(
            AssetComponent.objects.filter(organization=org).select_related(
                "property",
                "facility",
                "facility__property",
                "facility_space",
                "facility_space__unit",
                "vendor",
                "amc_vendor",
                "unit",
            )
        )

        category_counts: dict[str, int] = {}
        lifecycle_counts: dict[str, int] = {}
        warranty_counts = {"active": 0, "expiring": 0, "expired": 0, "not_covered": 0}
        amc_counts = {"active": 0, "expiring": 0, "expired": 0, "not_covered": 0}
        iot_counts = {"enabled": 0, "connected": 0, "offline": 0, "fault": 0, "not_connected": 0}

        acquisition_total = Decimal("0.00")
        book_value_total = Decimal("0.00")
        monthly_total = Decimal("0.00")

        warranty_watchlist: list[dict[str, object]] = []
        amc_watchlist: list[dict[str, object]] = []
        maintenance_watchlist: list[dict[str, object]] = []
        depreciation_watchlist: list[dict[str, object]] = []
        iot_watchlist: list[dict[str, object]] = []

        critical_assets = 0
        maintenance_due_30_days = 0
        warranty_expiring_90_days = 0
        amc_expiring_90_days = 0
        depreciating_assets = 0
        iot_connected_assets = 0

        for asset in assets:
            category_counts[asset.category] = category_counts.get(asset.category, 0) + 1
            lifecycle_counts[asset.lifecycle_stage] = lifecycle_counts.get(asset.lifecycle_stage, 0) + 1

            if asset.condition_rating in (
                AssetComponent.ConditionRating.POOR,
                AssetComponent.ConditionRating.CRITICAL,
            ):
                critical_assets += 1

            warranty_status = warranty_status_for(asset, today=today)
            warranty_counts[warranty_status] = warranty_counts.get(warranty_status, 0) + 1
            if warranty_status in {"expiring", "expired"}:
                warranty_watchlist.append(_asset_watch_row(asset))
            if warranty_status == "expiring":
                warranty_expiring_90_days += 1

            amc_status = amc_status_for(asset, today=today)
            amc_counts[amc_status] = amc_counts.get(amc_status, 0) + 1
            if amc_status in {"expiring", "expired"}:
                amc_watchlist.append(_asset_watch_row(asset))
            if amc_status == "expiring":
                amc_expiring_90_days += 1

            maintenance_status = maintenance_status_for(asset, today=today)
            if maintenance_status in {"overdue", "due_soon"}:
                maintenance_watchlist.append(_asset_watch_row(asset))
                maintenance_due_30_days += 1

            if asset.depreciation_enabled:
                depreciating_assets += 1
                acquisition_total += asset.acquisition_cost or Decimal("0.00")
                monthly_total += monthly_depreciation_for(asset) or Decimal("0.00")
                book_value_total += current_book_value_for(asset) or Decimal("0.00")
                depreciation_watchlist.append(_asset_watch_row(asset))

            if asset.is_iot_enabled:
                iot_counts["enabled"] += 1
                iot_counts[asset.iot_status] = iot_counts.get(asset.iot_status, 0) + 1
                iot_watchlist.append(_asset_watch_row(asset))
                if asset.iot_status == AssetComponent.IoTStatus.CONNECTED:
                    iot_connected_assets += 1
            else:
                iot_counts["not_connected"] += 1

        synced_this_month = JournalEntry.objects.filter(
            organization=org,
            source_type=JournalSourceType.ADJUSTMENT,
            reference__startswith="ASSET-DEPR-",
            reference__endswith=period_token,
        ).count()

        payload = {
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "total_assets": len(assets),
                "active_assets": sum(1 for asset in assets if asset.is_active),
                "critical_assets": critical_assets,
                "maintenance_due_30_days": maintenance_due_30_days,
                "warranty_expiring_90_days": warranty_expiring_90_days,
                "amc_expiring_90_days": amc_expiring_90_days,
                "depreciating_assets": depreciating_assets,
                "iot_connected_assets": iot_connected_assets,
            },
            "category_breakdown": [
                {"key": key, "count": count}
                for key, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "lifecycle_breakdown": [
                {"key": key, "count": count}
                for key, count in sorted(lifecycle_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "warranty_breakdown": [
                {"key": key, "count": count}
                for key, count in warranty_counts.items()
            ],
            "amc_breakdown": [
                {"key": key, "count": count}
                for key, count in amc_counts.items()
            ],
            "depreciation": {
                "tracked_assets": depreciating_assets,
                "total_acquisition_cost": _money(acquisition_total),
                "total_book_value": _money(book_value_total),
                "total_monthly_depreciation": _money(monthly_total),
                "synced_this_month": synced_this_month,
            },
            "iot": iot_counts,
            "maintenance_watchlist": sorted(
                maintenance_watchlist,
                key=lambda item: (item["maintenance_next_due_date"] or "9999-12-31", str(item["component_id"])),
            )[:8],
            "warranty_watchlist": sorted(
                warranty_watchlist,
                key=lambda item: (item["warranty_expiry"] or "9999-12-31", str(item["component_id"])),
            )[:8],
            "amc_watchlist": sorted(
                amc_watchlist,
                key=lambda item: (item["amc_end_date"] or "9999-12-31", str(item["component_id"])),
            )[:8],
            "depreciation_watchlist": sorted(
                depreciation_watchlist,
                key=lambda item: (item["component_id"],),
            )[:8],
            "iot_watchlist": sorted(
                iot_watchlist,
                key=lambda item: (str(item["iot_status"]), str(item["component_id"])),
            )[:8],
        }
        return Response(payload)


class FacilityAssetFilter(filters.FilterSet):
    warranty_before = filters.DateFilter(field_name="warranty_expiry", lookup_expr="lte")
    warranty_after = filters.DateFilter(field_name="warranty_expiry", lookup_expr="gte")
    maintenance_due_before = filters.DateFilter(field_name="maintenance_next_due_date", lookup_expr="lte")
    maintenance_due_after = filters.DateFilter(field_name="maintenance_next_due_date", lookup_expr="gte")
    amc_before = filters.DateFilter(field_name="amc_end_date", lookup_expr="lte")
    amc_after = filters.DateFilter(field_name="amc_end_date", lookup_expr="gte")

    class Meta:
        model = AssetComponent
        fields = [
            "property",
            "facility",
            "facility_space",
            "unit",
            "vendor",
            "amc_vendor",
            "category",
            "condition_rating",
            "lifecycle_stage",
            "depreciation_enabled",
            "is_iot_enabled",
            "iot_status",
            "is_active",
        ]


class FacilityAssetViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    filterset_class = FacilityAssetFilter
    search_fields = [
        "component_id",
        "name",
        "manufacturer",
        "model_number",
        "serial_number",
        "facility__facility_code",
        "facility__property__name",
    ]
    ordering_fields = [
        "component_id",
        "name",
        "maintenance_next_due_date",
        "warranty_expiry",
        "amc_end_date",
        "installation_date",
        "created_at",
    ]
    ordering = ["component_id"]
    queryset = AssetComponent.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related(
            "property",
            "facility",
            "facility__property",
            "facility_space",
            "facility_space__unit",
            "unit",
            "vendor",
            "amc_vendor",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return AssetComponentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return AssetComponentWriteSerializer
        return AssetComponentDetailSerializer

    @action(detail=True, methods=["post"], url_path="sync-depreciation")
    def sync_depreciation(self, request, pk=None):
        asset = self.get_object()
        journal = sync_asset_depreciation_journal(asset, actor=request.user)
        if not journal:
            return Response(
                {"detail": "Asset is not configured for depreciation sync."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "asset_id": asset.id,
                "journal_id": journal.id,
                "journal_number": journal.journal_number,
                "reference": journal.reference,
                "status": journal.status,
            }
        )

    @action(detail=False, methods=["post"], url_path="sync-depreciation")
    def sync_depreciation_bulk(self, request):
        eligible_assets = self.filter_queryset(
            self.get_queryset().filter(depreciation_enabled=True, is_active=True)
        )

        synced = 0
        skipped = 0
        journal_ids: list[int] = []
        for asset in eligible_assets[:250]:
            journal = sync_asset_depreciation_journal(asset, actor=request.user)
            if journal:
                synced += 1
                journal_ids.append(journal.id)
            else:
                skipped += 1

        return Response(
            {
                "synced": synced,
                "skipped": skipped,
                "journal_ids": journal_ids,
            }
        )
