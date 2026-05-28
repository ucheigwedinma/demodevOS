<script lang="ts">
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { InvitationItem, InvitationListResponse } from "$lib/types";

  interface RoleOption {
    id: number;
    name: string;
    slug: string;
  }

  // Form state
  let email = $state("");
  let firstName = $state("");
  let lastName = $state("");
  let roleId = $state<number | null>(null);
  let jobTitle = $state("");

  let sending = $state(false);
  let error = $state("");
  let successMessage = $state("");

  // Roles dropdown
  let roles = $state<RoleOption[]>([]);

  // Invitations list
  let invitations = $state<InvitationItem[]>([]);
  let loadingInvitations = $state(true);

  function formatDate(dateStr: string): string {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function formatRelative(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateStr);
  }

  async function fetchRoles() {
    try {
      const res = await api.get<{ results: RoleOption[] }>("/settings/roles/");
      roles = res.results ?? [];
    } catch {
      roles = [];
    }
  }

  async function fetchInvitations() {
    loadingInvitations = true;
    try {
      const res = await api.get<InvitationListResponse>("/iam/users/invitations/");
      invitations = res.results;
    } catch {
      invitations = [];
    } finally {
      loadingInvitations = false;
    }
  }

  async function handleSubmit() {
    error = "";
    successMessage = "";

    if (!email.trim()) {
      error = "Email address is required.";
      return;
    }

    sending = true;
    try {
      await api.post("/iam/users/", {
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        role_id: roleId,
        job_title: jobTitle.trim(),
      });
      successMessage = `Invitation sent to ${email.trim()}`;
      email = "";
      firstName = "";
      lastName = "";
      roleId = null;
      jobTitle = "";
      fetchInvitations();
    } catch (err: unknown) {
      const apiErr = err as { data?: { email?: string[]; detail?: string } };
      if (apiErr.data?.email?.[0]) {
        error = apiErr.data.email[0];
      } else if (apiErr.data?.detail) {
        error = apiErr.data.detail;
      } else {
        error = "Failed to send invitation. Please try again.";
      }
    } finally {
      sending = false;
    }
  }

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const DEV_SAMPLES = [
    { email: "ahmed.hassan@example.com", firstName: "Ahmed", lastName: "Hassan", jobTitle: "Senior Site Engineer" },
    { email: "sara.ali@example.com", firstName: "Sara", lastName: "Ali", jobTitle: "Sales Executive — Off-Plan" },
    { email: "omar.khalid@example.com", firstName: "Omar", lastName: "Khalid", jobTitle: "Financial Controller" },
  ];
  let devFillIdx = 0;
  function devFill() {
    const s = DEV_SAMPLES[devFillIdx % DEV_SAMPLES.length]; devFillIdx++;
    email = s.email; firstName = s.firstName; lastName = s.lastName; jobTitle = s.jobTitle;
    if (roles.length) roleId = roles[0].id;
  }

  $effect(() => {
    fetchRoles();
    fetchInvitations();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Invite User</h1>
      <p class="mt-1 text-sm text-neutral-500">Send an email invitation to add a new user to your organization.</p>
    </div>
    <a
      href="/iam/users"
      class="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-500 hover:text-neutral-700 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
      </svg>
      Back to directory
    </a>
  </div>

  <!-- Invite Form -->
  <div class="rounded-xl border border-neutral-200 bg-white divide-y divide-neutral-100">
    <div class="px-6 py-5">
      <h2 class="text-sm font-semibold text-neutral-900">New Invitation</h2>
      <p class="mt-0.5 text-xs text-neutral-400">The user will receive an email with a link to create their account.</p>
    </div>

    <form
      class="px-6 py-5 space-y-5"
      onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}
    >
      <!-- Email -->
      <div>
        <label class="block text-xs font-medium text-neutral-600 mb-1.5" for="invite-email">
          Email address <span class="text-red-400">*</span>
        </label>
        <input
          id="invite-email"
          type="email"
          bind:value={email}
          placeholder="name@company.com"
          required
          class="w-full max-w-md rounded-lg border border-neutral-300 px-3.5 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
        />
      </div>

      <!-- Name row -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-md">
        <div>
          <label class="block text-xs font-medium text-neutral-600 mb-1.5" for="invite-first-name">
            First name
          </label>
          <input
            id="invite-first-name"
            type="text"
            bind:value={firstName}
            placeholder="Jane"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-neutral-600 mb-1.5" for="invite-last-name">
            Last name
          </label>
          <input
            id="invite-last-name"
            type="text"
            bind:value={lastName}
            placeholder="Smith"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>
      </div>

      <!-- Role & Job Title row -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-md">
        <div>
          <label class="block text-xs font-medium text-neutral-600 mb-1.5" for="invite-role">
            Role
          </label>
          <select
            id="invite-role"
            bind:value={roleId}
            class="w-full appearance-none rounded-lg border border-neutral-300 px-3.5 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          >
            <option value={null}>None</option>
            {#each roles as role}
              <option value={role.id}>{role.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-neutral-600 mb-1.5" for="invite-job-title">
            Job title
          </label>
          <input
            id="invite-job-title"
            type="text"
            bind:value={jobTitle}
            placeholder="e.g. Project Manager"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>
      </div>

      <!-- Feedback -->
      {#if error}
        <div class="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-3 max-w-md">
          <svg class="w-4 h-4 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          <p class="text-sm text-red-700">{error}</p>
        </div>
      {/if}

      {#if successMessage}
        <div class="flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-3 max-w-md">
          <svg class="w-4 h-4 text-emerald-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <p class="text-sm text-emerald-700">{successMessage}</p>
        </div>
      {/if}

      <!-- Submit -->
      <div class="flex items-center gap-3">
        {#if isDev}
          <button type="button" onclick={devFill} class="px-4 py-2.5 text-sm font-semibold text-white bg-orange-500 rounded-lg hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button
          type="submit"
          disabled={sending || !email.trim()}
          class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {#if sending}
            <div class="w-4 h-4 border-2 border-neutral-400 border-t-white rounded-full animate-spin"></div>
            Sending...
          {:else}
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
            </svg>
            Send Invitation
          {/if}
        </button>
      </div>
    </form>
  </div>

  <!-- Recent Invitations -->
  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    <div class="px-6 py-5 border-b border-neutral-100">
      <h2 class="text-sm font-semibold text-neutral-900">Recent Invitations</h2>
      <p class="mt-0.5 text-xs text-neutral-400">Track the status of invitations sent from your organization.</p>
    </div>

    {#if loadingInvitations}
      <div class="flex items-center justify-center py-16">
        <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if invitations.length === 0}
      <div class="flex flex-col items-center justify-center py-16 text-center">
        <div class="text-neutral-300 mb-3">
          <svg class="mx-auto h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
          </svg>
        </div>
        <p class="text-sm text-neutral-500">No invitations sent yet</p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Email</th>
              <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Invited By</th>
              <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Sent</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each invitations as inv}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-3.5 text-sm text-neutral-900 font-medium">{inv.email}</td>
                <td class="px-5 py-3.5">
                  <StatusBadge status={inv.status} label={inv.status_display} />
                </td>
                <td class="px-5 py-3.5 text-sm text-neutral-500">{inv.invited_by_name}</td>
                <td class="px-5 py-3.5 text-sm text-neutral-500">{formatRelative(inv.created_at)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
