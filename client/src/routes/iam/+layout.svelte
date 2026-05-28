<script lang="ts">
  import { page } from "$app/stores";

  let { children } = $props();

  const menuSections = [
    {
      title: "Users",
      items: [
        { href: "/iam/users", label: "User Directory", exact: true },
        { href: "/iam/users/invite", label: "Create / Invite User" },
        { href: "/iam/users/profiles", label: "User Profiles" },
        { href: "/iam/users/status", label: "User Status" },
        { href: "/iam/users/groups", label: "User Groups" },
        { href: "/iam/users/lifecycle", label: "User Lifecycle" },
        { href: "/iam/users/linked-employees", label: "Linked Employees" },
        { href: "/iam/users/external", label: "External Users" },
      ],
    },
    {
      title: "API & System Access",
      items: [
        { href: "/iam/api-keys", label: "API Keys", exact: true },
        { href: "/iam/service-accounts", label: "Service Accounts" },
        { href: "/iam/webhooks", label: "Webhooks Authentication" },
        { href: "/iam/app-tokens", label: "Application Tokens" },
        { href: "/iam/integrations", label: "Third-party Integrations" },
      ],
    },
    {
      title: "Roles & Permissions",
      items: [
        { href: "/iam/roles", label: "Roles Library", exact: true },
        { href: "/iam/roles/create", label: "Create Role" },
        { href: "/iam/roles/permission-matrix", label: "Permission Matrix" },
        { href: "/iam/roles/module-access", label: "Module Access" },
        { href: "/iam/roles/feature-access", label: "Feature Access" },
        { href: "/iam/roles/data-access-scope", label: "Data Access Scope" },
        { href: "/iam/roles/role-assignment", label: "Role Assignment" },
      ],
    },
    {
      title: "Access Policies",
      items: [
        { href: "/iam/access-policies", label: "Access Rules", exact: true },
        { href: "/iam/access-policies/conditional", label: "Conditional Access" },
        { href: "/iam/access-policies/ip-restrictions", label: "IP Restrictions" },
        { href: "/iam/access-policies/device-restrictions", label: "Device Restrictions" },
        { href: "/iam/access-policies/location-restrictions", label: "Location Restrictions" },
        { href: "/iam/access-policies/time-based", label: "Time-based Access" },
        { href: "/iam/access-policies/session-duration", label: "Session Duration" },
      ],
    },
    {
      title: "Access Requests",
      items: [
        { href: "/iam/access-requests", label: "Request Access", exact: true },
        { href: "/iam/access-requests/approvals", label: "Approval Workflow" },
        { href: "/iam/access-requests/temporary", label: "Temporary Access" },
        { href: "/iam/access-requests/expiry", label: "Access Expiry" },
        { href: "/iam/access-requests/elevation", label: "Privilege Elevation" },
      ],
    },
    {
      title: "Authentication & Security",
      items: [
        { href: "/iam/auth", label: "Password Policies", exact: true },
        { href: "/iam/auth/mfa", label: "Multi-Factor Authentication" },
        { href: "/iam/auth/sso", label: "Single Sign-On (SSO)" },
        { href: "/iam/auth/oauth-saml", label: "OAuth / SAML" },
        { href: "/iam/auth/login-methods", label: "Login Methods" },
        { href: "/iam/auth/biometric", label: "Biometric Auth" },
        { href: "/iam/auth/sessions", label: "Session Management" },
      ],
    },
    {
      title: "Identity Federation",
      items: [
        { href: "/iam/federation/active-directory", label: "Active Directory" },
        { href: "/iam/federation/ldap", label: "LDAP" },
        { href: "/iam/federation/azure-ad", label: "Azure AD" },
        { href: "/iam/federation/google-workspace", label: "Google Workspace" },
        { href: "/iam/federation/external-idp", label: "External Identity Providers" },
      ],
    },
    {
      title: "Compliance & Monitoring",
      items: [
        { href: "/iam/compliance/access-reviews", label: "Access Reviews" },
        { href: "/iam/compliance/role-certification", label: "Role Certification" },
        { href: "/iam/compliance/dormant-accounts", label: "Dormant Account Detection" },
        { href: "/iam/compliance/privilege-risk", label: "Privilege Risk Analysis" },
        { href: "/iam/compliance/reports", label: "Compliance Reports" },
      ],
    },
  ];

  function isActive(href: string, exact?: boolean): boolean {
    if (exact) return $page.url.pathname === href;
    return $page.url.pathname.startsWith(href);
  }
</script>

<div class="h-screen flex flex-col bg-neutral-50 font-sans">
  <!-- Top Nav -->
  <header class="bg-neutral-900 shrink-0">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-6">
        <a href="/" class="text-lg">
          <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>
        </a>
        <span class="text-neutral-600">|</span>
        <h1 class="text-sm font-semibold text-white">Identity & Access Management</h1>
      </div>
      <a
        href="/"
        class="flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to app
      </a>
    </div>
  </header>

  <!-- Body -->
  <div class="max-w-7xl mx-auto px-6 flex gap-8 flex-1 min-h-0 w-full">
    <!-- Sidebar -->
    <aside class="w-56 shrink-0 overflow-y-auto py-8">
      {#each menuSections as section}
        <div class="mb-8">
          <p class="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-3 px-3">
            {section.title}
          </p>
          <nav class="space-y-0.5">
            {#each section.items as item}
              <a
                href={item.href}
                class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                       {isActive(item.href, item.exact)
                         ? 'bg-neutral-900 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700'}"
              >
                {item.label}
              </a>
            {/each}
          </nav>
        </div>
      {/each}
    </aside>

    <!-- Content -->
    <div class="flex-1 min-w-0 overflow-y-auto py-8">
      {@render children()}
    </div>
  </div>
</div>
