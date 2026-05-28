<script lang="ts">
  import AuditEventsList from "$lib/components/AuditEventsList.svelte";
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Login Activity</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Successful authentication events — who signed in, when, from where, and via which provider.
      For unsuccessful attempts see <a href="/settings/audit/failed-logins" class="underline underline-offset-2 hover:text-neutral-800">Failed Login Attempts</a>.
    </p>
  </div>

  <AuditEventsList
    eventTypes={["login_success"]}
    emptyText="No login activity recorded yet."
    showStatus={false}
  />
</div>
