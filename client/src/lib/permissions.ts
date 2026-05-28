import { onboarding } from "$lib/stores/onboarding.svelte";

const REPOSITORY_CREATOR_ROLE_SLUGS = new Set([
  "governance-officer",
  "developer-executive",
]);

/**
 * Check if the current user has a specific permission.
 * Org admins (permissions: ["*"]) always return true.
 */
export function can(subModule: string, action: string): boolean {
  const user = onboarding.user;
  if (!user?.organization) return false;
  const perms = user.organization.permissions;
  if (!perms) return false;
  if (perms.includes("*")) return true;
  return perms.includes(`${subModule}.${action}`);
}

/**
 * Check if the current user has any permission on a sub-module.
 */
export function canAny(subModule: string): boolean {
  const user = onboarding.user;
  if (!user?.organization) return false;
  const perms = user.organization.permissions;
  if (!perms) return false;
  if (perms.includes("*")) return true;
  return perms.some((p) => p.startsWith(`${subModule}.`));
}

/**
 * Only governance admin cohort should be able to create new repository records.
 */
export function canCreateRepositoryDocument(): boolean {
  const user = onboarding.user;
  if (!user) return false;
  if (user.is_superuser) return true;
  const org = user.organization;
  if (!org) return false;
  if (org.role === "admin") return true;
  const roleSlug = org.assigned_role?.slug ?? "";
  if (!REPOSITORY_CREATOR_ROLE_SLUGS.has(roleSlug)) return false;
  return can("documents.all", "upload_version");
}
