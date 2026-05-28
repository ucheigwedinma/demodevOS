<script lang="ts">
  import AuditEventsList from "$lib/components/AuditEventsList.svelte";
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Security Alerts</h1>
    <p class="mt-1 text-sm text-neutral-500">
      High-severity events that warrant immediate review — login-method or password-policy changes,
      revoked access grants, anomalous activity. Filter is set to severity ≥ high.
    </p>
  </div>

  <AuditEventsList
    severities={["high", "critical"]}
    emptyText="No high-severity alerts in the visible window."
  />
</div>
