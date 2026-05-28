<script lang="ts">
  import AuditEventsList from "$lib/components/AuditEventsList.svelte";
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Access Logs</h1>
    <p class="mt-1 text-sm text-neutral-500">
      The full IAM audit feed — every authentication, role change, permission update, and access-request decision.
      Drill into specific event types via the focused pages in the sidebar.
    </p>
  </div>

  <AuditEventsList
    emptyText="No audit events recorded yet."
  />
</div>
