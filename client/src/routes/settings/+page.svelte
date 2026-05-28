<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { CompanyProfile } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let loading = $state(true);
  let saving = $state(false);
  let form = $state<Partial<CompanyProfile>>({});
  let logoPreview = $state<string | null>(null);
  let logoFile = $state<File | null>(null);

  const INDUSTRY_OPTIONS = [
    "Real Estate Development",
    "Construction",
    "Property Management",
    "Architecture & Design",
    "Engineering",
    "Infrastructure",
    "Mixed-Use Development",
    "Commercial Real Estate",
    "Residential Development",
    "Other",
  ];

  const SIZE_OPTIONS = [
    { value: "1-10", label: "1-10 employees" },
    { value: "11-50", label: "11-50 employees" },
    { value: "51-200", label: "51-200 employees" },
    { value: "201-500", label: "201-500 employees" },
    { value: "500+", label: "500+ employees" },
  ];

  const MONTH_OPTIONS = [
    { value: 1, label: "January" },
    { value: 2, label: "February" },
    { value: 3, label: "March" },
    { value: 4, label: "April" },
    { value: 5, label: "May" },
    { value: 6, label: "June" },
    { value: 7, label: "July" },
    { value: 8, label: "August" },
    { value: 9, label: "September" },
    { value: 10, label: "October" },
    { value: 11, label: "November" },
    { value: 12, label: "December" },
  ];

  async function loadProfile() {
    try {
      const data = await api.get<CompanyProfile>("/settings/company-profile/");
      form = data;
      if (data.logo) logoPreview = data.logo;
    } catch {
      toast.error("Load failed", "Could not load company profile.");
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    try {
      if (logoFile) {
        const fd = new FormData();
        for (const [key, value] of Object.entries(form)) {
          if (key === "logo" || key === "created_at" || key === "updated_at" || key === "id") continue;
          if (value !== null && value !== undefined) fd.append(key, String(value));
        }
        fd.append("logo", logoFile);
        const token = localStorage.getItem("access_token");
        await fetch("/api/settings/company-profile/", {
          method: "PATCH",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: fd,
        });
      } else {
        const { id, created_at, updated_at, logo, ...payload } = form as CompanyProfile;
        await api.patch<CompanyProfile>("/settings/company-profile/", payload);
      }
      toast.success("Saved", "Company profile updated successfully.");
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    } finally {
      saving = false;
    }
  }

  function handleLogoSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    logoFile = file;
    logoPreview = URL.createObjectURL(file);
  }

  function removeLogo() {
    logoFile = null;
    logoPreview = null;
    form.logo = null;
  }

  $effect(() => {
    loadProfile();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else}
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h2 class="text-xl font-bold text-neutral-800">Company Profile</h2>
      <p class="mt-1 text-sm text-neutral-500">Manage your organization's basic information and branding.</p>
    </div>
    <button
      onclick={handleSave}
      disabled={saving}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
    >
      {saving ? "Saving..." : "Save Changes"}
    </button>
  </div>

  <div class="space-y-6 max-w-3xl">
    <!-- Basic Information -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Basic Information</h3>
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div class="sm:col-span-2">
          <label for="name" class="block text-sm font-medium text-neutral-700 mb-1.5">Company Name</label>
          <input id="name" type="text" bind:value={form.name} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div>
          <label for="legal_name" class="block text-sm font-medium text-neutral-700 mb-1.5">Legal Name</label>
          <input id="legal_name" type="text" bind:value={form.legal_name} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div>
          <label for="trading_name" class="block text-sm font-medium text-neutral-700 mb-1.5">Trading Name</label>
          <input id="trading_name" type="text" bind:value={form.trading_name} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div>
          <label for="industry" class="block text-sm font-medium text-neutral-700 mb-1.5">Industry</label>
          <select id="industry" bind:value={form.industry} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow">
            <option value="">Select industry</option>
            {#each INDUSTRY_OPTIONS as opt}
              <option value={opt}>{opt}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for="size" class="block text-sm font-medium text-neutral-700 mb-1.5">Company Size</label>
          <select id="size" bind:value={form.size} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow">
            <option value="">Select size</option>
            {#each SIZE_OPTIONS as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>
        <div class="sm:col-span-2">
          <label for="description" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <textarea id="description" rows="3" bind:value={form.description} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow resize-none" placeholder="Brief description of your organization"></textarea>
        </div>
        <div>
          <label for="founded_date" class="block text-sm font-medium text-neutral-700 mb-1.5">Founded Date</label>
          <DateInput id="founded_date" bind:value={form.founded_date} />
        </div>
      </div>
    </section>

    <!-- Legal & Tax -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Legal & Tax</h3>
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div>
          <label for="registration_number" class="block text-sm font-medium text-neutral-700 mb-1.5">Registration Number</label>
          <input id="registration_number" type="text" bind:value={form.registration_number} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div>
          <label for="tax_id" class="block text-sm font-medium text-neutral-700 mb-1.5">Tax ID</label>
          <input id="tax_id" type="text" bind:value={form.tax_id} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div>
          <label for="fiscal_year_start_month" class="block text-sm font-medium text-neutral-700 mb-1.5">Fiscal Year Start</label>
          <select id="fiscal_year_start_month" bind:value={form.fiscal_year_start_month} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow">
            {#each MONTH_OPTIONS as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>
      </div>
    </section>

    <!-- Contact Details -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Contact Details</h3>
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div>
          <label for="email" class="block text-sm font-medium text-neutral-700 mb-1.5">Email</label>
          <input id="email" type="email" bind:value={form.email} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" placeholder="info@company.com" />
        </div>
        <div>
          <label for="phone" class="block text-sm font-medium text-neutral-700 mb-1.5">Phone</label>
          <input id="phone" type="tel" bind:value={form.phone} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" placeholder="+1 (555) 000-0000" />
        </div>
        <div class="sm:col-span-2">
          <label for="website" class="block text-sm font-medium text-neutral-700 mb-1.5">Website</label>
          <input id="website" type="url" bind:value={form.website} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" placeholder="https://www.company.com" />
        </div>
      </div>
    </section>

    <!-- Address -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Address</h3>
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div class="sm:col-span-2">
          <label for="address_line_1" class="block text-sm font-medium text-neutral-700 mb-1.5">Address Line 1</label>
          <input id="address_line_1" type="text" bind:value={form.address_line_1} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" placeholder="Street address" />
        </div>
        <div class="sm:col-span-2">
          <label for="address_line_2" class="block text-sm font-medium text-neutral-700 mb-1.5">Address Line 2</label>
          <input id="address_line_2" type="text" bind:value={form.address_line_2} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" placeholder="Suite, floor, etc." />
        </div>
        <div>
          <label for="city" class="block text-sm font-medium text-neutral-700 mb-1.5">City</label>
          <input id="city" type="text" bind:value={form.city} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div>
          <label for="state_province" class="block text-sm font-medium text-neutral-700 mb-1.5">State / Province</label>
          <input id="state_province" type="text" bind:value={form.state_province} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div>
          <label for="postal_code" class="block text-sm font-medium text-neutral-700 mb-1.5">Postal Code</label>
          <input id="postal_code" type="text" bind:value={form.postal_code} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div>
          <label for="country" class="block text-sm font-medium text-neutral-700 mb-1.5">Country</label>
          <input id="country" type="text" bind:value={form.country} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
      </div>
    </section>

    <!-- Branding -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Branding</h3>
      <div>
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label class="block text-sm font-medium text-neutral-700 mb-3">Company Logo</label>
        {#if logoPreview}
          <div class="flex items-center gap-5">
            <div class="h-20 w-20 rounded-xl border border-neutral-200 bg-neutral-50 flex items-center justify-center overflow-hidden">
              <img src={logoPreview} alt="Logo preview" class="h-full w-full object-contain" />
            </div>
            <div class="flex gap-2">
              <label class="cursor-pointer rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
                Change
                <input type="file" accept="image/*" onchange={handleLogoSelect} class="hidden" />
              </label>
              <button onclick={removeLogo} class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors">
                Remove
              </button>
            </div>
          </div>
        {:else}
          <label class="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-neutral-300 bg-neutral-50 py-8 hover:border-neutral-400 hover:bg-neutral-100 transition-colors">
            <svg class="w-8 h-8 text-neutral-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
            </svg>
            <span class="text-sm font-medium text-neutral-600">Click to upload logo</span>
            <span class="text-xs text-neutral-400 mt-1">PNG, JPG, SVG up to 2MB</span>
            <input type="file" accept="image/*" onchange={handleLogoSelect} class="hidden" />
          </label>
        {/if}
      </div>
    </section>
  </div>
{/if}
