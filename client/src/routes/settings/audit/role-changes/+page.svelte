<script lang="ts">
  import AuditEventsList from "$lib/components/AuditEventsList.svelte";
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Role Changes</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Role assignments and removals on individual users. For changes to a role's permission matrix, see
      <a href="/settings/audit/permission-changes" class="underline underline-offset-2 hover:text-neutral-800">Permission Changes</a>.
    </p>
  </div>

  <AuditEventsList
    eventTypes={["role_assigned", "role_unassigned"]}
    emptyText="No role assignments recorded yet."
    showStatus={false}
  />
</div>
