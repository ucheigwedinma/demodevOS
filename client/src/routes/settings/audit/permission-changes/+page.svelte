<script lang="ts">
  import AuditEventsList from "$lib/components/AuditEventsList.svelte";
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Permission Changes</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Audit trail of role-permission edits. Each event records the role, the actor, and the change set in metadata.
      For role assignments to users, see <a href="/settings/audit/role-changes" class="underline underline-offset-2 hover:text-neutral-800">Role Changes</a>.
    </p>
  </div>

  <AuditEventsList
    eventTypes={["role_permissions_changed"]}
    emptyText="No permission changes recorded yet."
    showStatus={false}
  />
</div>
