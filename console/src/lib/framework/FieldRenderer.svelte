<script lang="ts">
  import type { FormFieldDef } from "./types";

  let {
    field,
    value = "",
    error,
    onchange,
  }: {
    field: FormFieldDef;
    value: unknown;
    error?: string;
    onchange: (value: unknown) => void;
  } = $props();

  let inputClasses = "w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent";
  let errorClasses = $derived(error ? "border-red-300" : "border-neutral-200");
</script>

<div class="{field.gridSpan === 2 ? 'col-span-2' : ''}">
  <!-- svelte-ignore a11y_label_has_associated_control -->
  <label class="block text-sm font-medium text-neutral-700 mb-1">
    {field.label}
    {#if field.required}<span class="text-red-500">*</span>{/if}
  </label>

  {#if field.type === "textarea"}
    <textarea
      value={value as string ?? ""}
      oninput={(e) => onchange(e.currentTarget.value)}
      placeholder={field.placeholder}
      rows="3"
      class="{inputClasses} {errorClasses} resize-none"
    ></textarea>
  {:else if field.type === "select" && field.options}
    <select
      value={value as string ?? ""}
      onchange={(e) => onchange(e.currentTarget.value)}
      class="{inputClasses} {errorClasses} bg-white"
    >
      <option value="">Select {field.label}...</option>
      {#each field.options as opt}
        <option value={opt.value}>{opt.label}</option>
      {/each}
    </select>
  {:else if field.type === "boolean"}
    <label class="flex items-center gap-2">
      <input
        type="checkbox"
        checked={!!value}
        onchange={(e) => onchange(e.currentTarget.checked)}
        class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
      />
      <span class="text-sm text-neutral-600">{field.placeholder ?? field.label}</span>
    </label>
  {:else if field.type === "readonly"}
    <p class="px-3 py-2 text-sm text-neutral-500 bg-neutral-50 rounded-lg border border-neutral-200">
      {value ?? "-"}
    </p>
  {:else}
    <input
      type={field.type === "number" || field.type === "currency" ? "number" : field.type === "date" ? "date" : field.type === "datetime" ? "datetime-local" : "text"}
      value={value as string ?? ""}
      oninput={(e) => onchange(field.type === "number" || field.type === "currency" ? Number(e.currentTarget.value) : e.currentTarget.value)}
      placeholder={field.placeholder}
      step={field.type === "currency" ? "0.01" : undefined}
      class="{inputClasses} {errorClasses}"
    />
  {/if}

  {#if error}
    <p class="mt-1 text-xs text-red-600">{error}</p>
  {:else if field.helpText}
    <p class="mt-1 text-xs text-neutral-500">{field.helpText}</p>
  {/if}
</div>
