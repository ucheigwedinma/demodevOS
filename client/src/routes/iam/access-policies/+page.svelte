<script lang="ts">
  import AccessPolicyList from "$lib/components/AccessPolicyList.svelte";

  const KIND_LINKS = [
    { kind: "ip_restrictions", label: "IP", href: "/iam/access-policies/ip-restrictions" },
    { kind: "time_based", label: "Time", href: "/iam/access-policies/time-based" },
    { kind: "location_restrictions", label: "Location", href: "/iam/access-policies/location-restrictions" },
    { kind: "device_restrictions", label: "Device", href: "/iam/access-policies/device-restrictions" },
    { kind: "session_duration", label: "Session", href: "/iam/access-policies/session-duration" },
    { kind: "conditional", label: "Conditional", href: "/iam/access-policies/conditional" },
  ];
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Access Policies</h1>
    <p class="mt-1 text-sm text-neutral-500">
      All access policies for your organisation, regardless of kind. Use the dedicated kind pages
      below to create new policies; this view is the canonical inventory + status board.
    </p>
  </div>

  <div class="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-xs text-yellow-800">
    <p class="font-medium mb-1">Enforcement is opt-in</p>
    <p>
      Policies are stored and testable from this UI, but enforcement at request time requires the
      <code class="bg-white px-1 rounded">apps.accounts.policy_middleware.AccessPolicyMiddleware</code>
      to be added to the project's <code class="bg-white px-1 rounded">MIDDLEWARE</code>. This is
      deliberately not auto-wired so the integration can be staged and validated. Use the Test
      button on each row to dry-run a policy without enabling enforcement.
    </p>
  </div>

  <div class="grid gap-2 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
    {#each KIND_LINKS as link}
      <a href={link.href}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-3 text-center text-sm font-medium text-neutral-700 hover:border-neutral-400 hover:shadow-sm transition-all">
        {link.label} →
      </a>
    {/each}
  </div>

  <AccessPolicyList showKindColumn />
</div>
