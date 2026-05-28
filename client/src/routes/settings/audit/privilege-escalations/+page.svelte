<script lang="ts">
  import AuditEventsList from "$lib/components/AuditEventsList.svelte";
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Privilege Escalations</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Approved privilege-elevation requests ("sudo") and any access grants that were
      revoked early or auto-revoked at expiry. Inspect rows for the requested role + duration.
    </p>
  </div>

  <AuditEventsList
    eventTypes={[
      "access_request_approved",
      "access_request_revoked",
      "access_grant_auto_revoked",
    ]}
    emptyText="No privilege-elevation events recorded yet."
    showStatus={false}
  />
</div>
