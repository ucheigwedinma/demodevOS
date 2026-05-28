<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { CommunicationBrandingSettings } from "$lib/types";

  type Tab = "email" | "notifications" | "sms" | "letterhead" | "disclaimers" | "signature";
  let activeTab = $state<Tab>("email");

  let loading = $state(true);
  let saving = $state(false);
  let form = $state<Partial<CommunicationBrandingSettings>>({});

  // Digital Signature tab — provider info from existing endpoint
  let signatureProviders = $state<Array<{ key: string; label: string }>>([]);
  let defaultProvider = $state("");

  const tabs: { key: Tab; label: string }[] = [
    { key: "email", label: "Email Branding" },
    { key: "notifications", label: "Notifications" },
    { key: "sms", label: "SMS" },
    { key: "letterhead", label: "Letterhead" },
    { key: "disclaimers", label: "Disclaimers" },
    { key: "signature", label: "Digital Signature" },
  ];

  async function loadSettings() {
    try {
      const [settingsData, providerData] = await Promise.all([
        api.get<CommunicationBrandingSettings>("/settings/communication-branding/"),
        api
          .get<{ providers: Array<{ key: string; label: string }>; default_provider: string }>(
            "/documents/control/signatures/providers/"
          )
          .catch(() => null),
      ]);
      form = settingsData;
      if (providerData) {
        signatureProviders = providerData.providers;
        defaultProvider = providerData.default_provider;
      }
    } catch {
      toast.error("Load failed", "Could not load communication & branding settings.");
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    try {
      const { id, created_at, updated_at, letterhead_paper_size_display, ...payload } =
        form as CommunicationBrandingSettings;
      const data = await api.patch<CommunicationBrandingSettings>(
        "/settings/communication-branding/",
        payload
      );
      form = data;
      toast.success("Saved", "Communication & branding settings updated.");
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    loadSettings();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div
      class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"
    ></div>
  </div>
{:else}
  <!-- Header -->
  <div class="mb-8 flex items-center justify-between">
    <div>
      <h2 class="text-xl font-bold text-neutral-800">Communication & Branding</h2>
      <p class="mt-1 text-sm text-neutral-500">
        Configure external-facing email templates, notification branding, SMS settings, letterhead
        formats, disclaimers, and digital signature configuration.
      </p>
    </div>
    <button
      onclick={handleSave}
      disabled={saving}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
    >
      {saving ? "Saving..." : "Save Changes"}
    </button>
  </div>

  <!-- Tabs -->
  <div class="mb-6 border-b border-neutral-200">
    <nav class="-mb-px flex gap-6">
      {#each tabs as tab}
        <button
          onclick={() => (activeTab = tab.key)}
          class="whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium transition-colors {activeTab ===
          tab.key
            ? 'border-neutral-800 text-neutral-800'
            : 'border-transparent text-neutral-500 hover:border-neutral-300 hover:text-neutral-700'}"
        >
          {tab.label}
        </button>
      {/each}
    </nav>
  </div>

  <div class="max-w-3xl space-y-6">
    <!-- ─── Email Branding ──────────────────────────────────────────── -->
    {#if activeTab === "email"}
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Sender Configuration</h3>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label for="email_sender_name" class="mb-1.5 block text-sm font-medium text-neutral-700"
              >Sender Name</label
            >
            <input
              id="email_sender_name"
              type="text"
              bind:value={form.email_sender_name}
              placeholder="e.g. Acme Properties"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
            <p class="mt-1 text-xs text-neutral-500">
              Display name for outbound emails.
            </p>
          </div>
          <div>
            <label
              for="email_sender_address"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Sender Email</label
            >
            <input
              id="email_sender_address"
              type="email"
              bind:value={form.email_sender_address}
              placeholder="noreply@example.com"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
          </div>
          <div>
            <label for="email_reply_to" class="mb-1.5 block text-sm font-medium text-neutral-700"
              >Reply-To Address</label
            >
            <input
              id="email_reply_to"
              type="email"
              bind:value={form.email_reply_to}
              placeholder="support@example.com"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
          </div>
          <div>
            <label
              for="email_primary_color"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Brand Color</label
            >
            <div class="flex gap-2">
              <input
                type="color"
                bind:value={form.email_primary_color}
                class="h-[42px] w-12 cursor-pointer rounded-lg border border-neutral-300 p-1"
              />
              <input
                id="email_primary_color"
                type="text"
                bind:value={form.email_primary_color}
                placeholder="#000000"
                maxlength="7"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
              />
            </div>
          </div>
        </div>
        <div class="mt-4">
          <label for="email_logo_url" class="mb-1.5 block text-sm font-medium text-neutral-700"
            >Logo URL</label
          >
          <input
            id="email_logo_url"
            type="url"
            bind:value={form.email_logo_url}
            placeholder="https://example.com/logo.png"
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
          />
          <p class="mt-1 text-xs text-neutral-500">
            Logo displayed in email headers. Leave blank to use the organization logo.
          </p>
        </div>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Email Header Template</h3>
        <textarea
          bind:value={form.email_header_html}
          rows="6"
          placeholder="<div style='...'> Custom HTML header </div>"
          class="w-full resize-none rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 font-mono text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
        ></textarea>
        <p class="mt-1 text-xs text-neutral-500">
          HTML injected as the header in outbound email templates. Supports inline CSS.
        </p>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Email Footer Template</h3>
        <textarea
          bind:value={form.email_footer_html}
          rows="6"
          placeholder="<div style='...'> Custom HTML footer </div>"
          class="w-full resize-none rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 font-mono text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
        ></textarea>
        <p class="mt-1 text-xs text-neutral-500">
          HTML injected as the footer in outbound email templates. Supports inline CSS.
        </p>
      </section>

    <!-- ─── Notification Branding ───────────────────────────────────── -->
    {:else if activeTab === "notifications"}
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Notification Appearance</h3>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label
              for="notification_app_name"
              class="mb-1.5 block text-sm font-medium text-neutral-700">App Display Name</label
            >
            <input
              id="notification_app_name"
              type="text"
              bind:value={form.notification_app_name}
              placeholder="e.g. Acme Properties"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
            <p class="mt-1 text-xs text-neutral-500">
              Name displayed in notification titles and push messages.
            </p>
          </div>
          <div>
            <label
              for="notification_logo_url"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Notification Logo URL</label
            >
            <input
              id="notification_logo_url"
              type="url"
              bind:value={form.notification_logo_url}
              placeholder="https://example.com/icon.png"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
          </div>
          <div>
            <label
              for="notification_brand_color"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Brand Color</label
            >
            <div class="flex gap-2">
              <input
                type="color"
                bind:value={form.notification_brand_color}
                class="h-[42px] w-12 cursor-pointer rounded-lg border border-neutral-300 p-1"
              />
              <input
                id="notification_brand_color"
                type="text"
                bind:value={form.notification_brand_color}
                placeholder="#000000"
                maxlength="7"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
              />
            </div>
          </div>
          <div>
            <label
              for="notification_accent_color"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Accent Color</label
            >
            <div class="flex gap-2">
              <input
                type="color"
                bind:value={form.notification_accent_color}
                class="h-[42px] w-12 cursor-pointer rounded-lg border border-neutral-300 p-1"
              />
              <input
                id="notification_accent_color"
                type="text"
                bind:value={form.notification_accent_color}
                placeholder="#3B82F6"
                maxlength="7"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
              />
            </div>
          </div>
        </div>

        <div
          class="mt-5 flex items-center justify-between border-t border-neutral-100 pt-5"
        >
          <div>
            <p class="text-sm font-medium text-neutral-800">Include Logo in Notifications</p>
            <p class="mt-0.5 text-xs text-neutral-500">
              Display the notification logo in email and push notifications.
            </p>
          </div>
          <!-- svelte-ignore a11y_consider_explicit_label -->
          <button
            type="button"
            onclick={() => (form.notification_include_logo = !form.notification_include_logo)}
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                   {form.notification_include_logo ? 'bg-neutral-800' : 'bg-neutral-200'}"
            role="switch"
            aria-checked={form.notification_include_logo}
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                     {form.notification_include_logo ? 'translate-x-5' : 'translate-x-0.5'}"
              style="margin-top: 2px;"
            ></span>
          </button>
        </div>
      </section>

    <!-- ─── SMS Configuration ───────────────────────────────────────── -->
    {:else if activeTab === "sms"}
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-sm font-semibold text-neutral-800">SMS Configuration</h3>
          <button
            type="button"
            onclick={() => (form.sms_enabled = !form.sms_enabled)}
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                   {form.sms_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
            role="switch"
            aria-checked={form.sms_enabled}
            aria-label="Enable SMS"
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                     {form.sms_enabled ? 'translate-x-5' : 'translate-x-0.5'}"
              style="margin-top: 2px;"
            ></span>
          </button>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2" class:opacity-50={!form.sms_enabled}>
          <div>
            <label for="sms_sender_id" class="mb-1.5 block text-sm font-medium text-neutral-700"
              >Sender ID / Short Code</label
            >
            <input
              id="sms_sender_id"
              type="text"
              bind:value={form.sms_sender_id}
              placeholder="e.g. ACMEPROP"
              disabled={!form.sms_enabled}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 disabled:cursor-not-allowed"
            />
            <p class="mt-1 text-xs text-neutral-500">
              Alphanumeric sender ID or short code displayed to recipients.
            </p>
          </div>
          <div>
            <label for="sms_prefix" class="mb-1.5 block text-sm font-medium text-neutral-700"
              >Message Prefix</label
            >
            <input
              id="sms_prefix"
              type="text"
              bind:value={form.sms_prefix}
              placeholder="e.g. [Acme]"
              disabled={!form.sms_enabled}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 disabled:cursor-not-allowed"
            />
            <p class="mt-1 text-xs text-neutral-500">Prepended to all outbound SMS messages.</p>
          </div>
          <div>
            <label
              for="sms_opt_out_message"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Opt-Out Message</label
            >
            <input
              id="sms_opt_out_message"
              type="text"
              bind:value={form.sms_opt_out_message}
              placeholder="Reply STOP to opt out."
              disabled={!form.sms_enabled}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 disabled:cursor-not-allowed"
            />
          </div>
          <div>
            <label
              for="sms_character_limit"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Character Limit</label
            >
            <input
              id="sms_character_limit"
              type="number"
              min="50"
              max="1600"
              bind:value={form.sms_character_limit}
              disabled={!form.sms_enabled}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 disabled:cursor-not-allowed"
            />
            <p class="mt-1 text-xs text-neutral-500">
              Standard SMS limit is 160 characters. Multipart up to 1,600.
            </p>
          </div>
        </div>
      </section>

    <!-- ─── Letterhead ──────────────────────────────────────────────── -->
    {:else if activeTab === "letterhead"}
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Page Setup</h3>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label
              for="letterhead_paper_size"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Paper Size</label
            >
            <select
              id="letterhead_paper_size"
              bind:value={form.letterhead_paper_size}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            >
              <option value="a4">A4</option>
              <option value="letter">Letter</option>
              <option value="legal">Legal</option>
            </select>
          </div>
          <div>
            <label
              for="letterhead_margin_top_mm"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Top Margin (mm)</label
            >
            <input
              id="letterhead_margin_top_mm"
              type="number"
              min="0"
              max="100"
              bind:value={form.letterhead_margin_top_mm}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
          </div>
          <div>
            <label
              for="letterhead_margin_bottom_mm"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Bottom Margin (mm)</label
            >
            <input
              id="letterhead_margin_bottom_mm"
              type="number"
              min="0"
              max="100"
              bind:value={form.letterhead_margin_bottom_mm}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
          </div>
        </div>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Watermark</h3>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label
              for="letterhead_watermark_text"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Watermark Text</label
            >
            <input
              id="letterhead_watermark_text"
              type="text"
              bind:value={form.letterhead_watermark_text}
              placeholder="e.g. DRAFT, CONFIDENTIAL"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
          </div>
          <div>
            <label
              for="letterhead_watermark_opacity"
              class="mb-1.5 block text-sm font-medium text-neutral-700"
              >Opacity ({form.letterhead_watermark_opacity ?? 15}%)</label
            >
            <input
              id="letterhead_watermark_opacity"
              type="range"
              min="0"
              max="100"
              bind:value={form.letterhead_watermark_opacity}
              class="mt-2 w-full accent-neutral-800"
            />
          </div>
        </div>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Letterhead Header</h3>
        <textarea
          bind:value={form.letterhead_header_html}
          rows="6"
          placeholder="<div style='...'> Organization name, address, logo </div>"
          class="w-full resize-none rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 font-mono text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
        ></textarea>
        <p class="mt-1 text-xs text-neutral-500">
          HTML header for generated documents (contracts, letters). Supports inline CSS.
        </p>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Letterhead Footer</h3>
        <textarea
          bind:value={form.letterhead_footer_html}
          rows="4"
          placeholder="<div style='...'> Registration details, legal disclaimers </div>"
          class="w-full resize-none rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 font-mono text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
        ></textarea>
      </section>

      <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-4 py-3">
        <p class="text-xs text-neutral-500">
          <span class="font-semibold text-neutral-600">Note:</span> PDF report headers, footers, and
          page layout are configured separately in
          <a
            href="/settings/reporting-engine"
            class="font-medium text-neutral-700 underline underline-offset-2 hover:text-neutral-800"
            >Reporting Engine</a
          > settings.
        </p>
      </div>

    <!-- ─── Document Footer Disclaimers ─────────────────────────────── -->
    {:else if activeTab === "disclaimers"}
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Default Disclaimer</h3>
        <textarea
          bind:value={form.default_footer_disclaimer}
          rows="3"
          placeholder="Applied to all documents unless overridden by a type-specific disclaimer below."
          class="w-full resize-none rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
        ></textarea>
        <p class="mt-1 text-xs text-neutral-500">
          Fallback disclaimer appended to generated documents when no type-specific disclaimer is
          set.
        </p>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Contract Disclaimer</h3>
        <textarea
          bind:value={form.contract_footer_disclaimer}
          rows="3"
          placeholder="Legal disclaimer appended to contract documents..."
          class="w-full resize-none rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
        ></textarea>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Invoice Disclaimer</h3>
        <textarea
          bind:value={form.invoice_footer_disclaimer}
          rows="3"
          placeholder="Payment terms and conditions appended to invoices..."
          class="w-full resize-none rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
        ></textarea>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Report Disclaimer</h3>
        <textarea
          bind:value={form.report_footer_disclaimer}
          rows="3"
          placeholder="Confidentiality notice appended to generated reports..."
          class="w-full resize-none rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
        ></textarea>
      </section>

    <!-- ─── Digital Signature ───────────────────────────────────────── -->
    {:else if activeTab === "signature"}
      <!-- Provider info (read-only) -->
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Configured Providers</h3>
        {#if signatureProviders.length > 0}
          <div class="flex flex-wrap gap-2">
            {#each signatureProviders as provider}
              <span
                class="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium {provider.key ===
                defaultProvider
                  ? 'bg-neutral-800 text-white'
                  : 'bg-neutral-100 text-neutral-700'}"
              >
                {provider.label}
                {#if provider.key === defaultProvider}
                  <span class="ml-1.5 text-[10px] font-normal opacity-75">Default</span>
                {/if}
              </span>
            {/each}
          </div>
        {:else}
          <p class="text-sm text-neutral-500">No signature providers configured.</p>
        {/if}
        <p class="mt-3 text-xs text-neutral-500">
          Manage signature providers in
          <a
            href="/settings/document-automation"
            class="font-medium text-neutral-700 underline underline-offset-2 hover:text-neutral-800"
            >Document Automation</a
          > settings.
        </p>
      </section>

      <!-- Signature email branding -->
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Signature Request Email</h3>
        <div class="space-y-4">
          <div>
            <label
              for="signature_email_subject"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Email Subject</label
            >
            <input
              id="signature_email_subject"
              type="text"
              bind:value={form.signature_email_subject}
              placeholder="Signature requested: {'{document_title}'}"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
            <p class="mt-1 text-xs text-neutral-500">
              Placeholders: <code class="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">{'{document_title}'}</code>,
              <code class="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">{'{signer_name}'}</code>,
              <code class="rounded bg-neutral-100 px-1 py-0.5 text-[11px]">{'{organization_name}'}</code>
            </p>
          </div>
          <div>
            <label
              for="signature_email_body"
              class="mb-1.5 block text-sm font-medium text-neutral-700">Email Body</label
            >
            <textarea
              id="signature_email_body"
              bind:value={form.signature_email_body}
              rows="5"
              placeholder="Please review and sign the attached document..."
              class="w-full resize-none rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            ></textarea>
          </div>
        </div>
      </section>

      <!-- Signature settings -->
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="mb-5 text-sm font-semibold text-neutral-800">Reminders & Expiry</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-neutral-800">Send Reminders</p>
              <p class="mt-0.5 text-xs text-neutral-500">
                Automatically remind signers who haven't completed signing.
              </p>
            </div>
            <!-- svelte-ignore a11y_consider_explicit_label -->
            <button
              type="button"
              onclick={() => (form.signature_reminder_enabled = !form.signature_reminder_enabled)}
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                     {form.signature_reminder_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
              role="switch"
              aria-checked={form.signature_reminder_enabled}
            >
              <span
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                       {form.signature_reminder_enabled ? 'translate-x-5' : 'translate-x-0.5'}"
                style="margin-top: 2px;"
              ></span>
            </button>
          </div>

          {#if form.signature_reminder_enabled}
            <div>
              <label
                for="signature_reminder_frequency_hours"
                class="mb-1.5 block text-sm font-medium text-neutral-700"
                >Reminder Frequency (hours)</label
              >
              <input
                id="signature_reminder_frequency_hours"
                type="number"
                min="1"
                max="720"
                bind:value={form.signature_reminder_frequency_hours}
                class="w-full max-w-xs rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
              />
              <p class="mt-1 text-xs text-neutral-500">
                How often to send reminder emails (1–720 hours).
              </p>
            </div>
          {/if}

          <div>
            <label
              for="signature_expiry_days"
              class="mb-1.5 block text-sm font-medium text-neutral-700"
              >Signature Expiry (days)</label
            >
            <input
              id="signature_expiry_days"
              type="number"
              min="1"
              max="365"
              bind:value={form.signature_expiry_days}
              class="w-full max-w-xs rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
            <p class="mt-1 text-xs text-neutral-500">
              Days before an unsigned request expires automatically.
            </p>
          </div>

          <div class="flex items-center justify-between border-t border-neutral-100 pt-4">
            <div>
              <p class="text-sm font-medium text-neutral-800">Apply Organization Branding</p>
              <p class="mt-0.5 text-xs text-neutral-500">
                Include organization logo and colors in signature request emails.
              </p>
            </div>
            <!-- svelte-ignore a11y_consider_explicit_label -->
            <button
              type="button"
              onclick={() => (form.signature_branding_enabled = !form.signature_branding_enabled)}
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                     {form.signature_branding_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
              role="switch"
              aria-checked={form.signature_branding_enabled}
            >
              <span
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                       {form.signature_branding_enabled ? 'translate-x-5' : 'translate-x-0.5'}"
                style="margin-top: 2px;"
              ></span>
            </button>
          </div>
        </div>
      </section>
    {/if}
  </div>
{/if}
