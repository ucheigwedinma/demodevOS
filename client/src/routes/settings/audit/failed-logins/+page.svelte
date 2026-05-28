<script lang="ts">
  import AuditEventsList from "$lib/components/AuditEventsList.svelte";
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Failed Login Attempts</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Authentication failures: wrong password, expired credentials, OTP failures, blocked accounts.
      Spikes here are an early indicator of credential-stuffing or targeted attacks.
    </p>
  </div>

  <AuditEventsList
    eventTypes={["login_failed", "otp_failed"]}
    emptyText="No failed login attempts in the visible window."
    showStatus={false}
  />
</div>
