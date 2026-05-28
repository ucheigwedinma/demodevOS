<script lang="ts">
  import { api } from "$lib/api";
  import type { EmployeeChoice } from "$lib/types";

  interface Props {
    value: string;
    id?: string;
    disabled?: boolean;
    hasError?: boolean;
  }

  let { value = $bindable(""), id = "emp-select", disabled = false, hasError = false }: Props = $props();

  let options = $state<EmployeeChoice[]>([]);
  let loaded = $state(false);

  async function fetchOptions() {
    try {
      options = await api.get<EmployeeChoice[]>("/hr/employee-records/choices/");
    } catch {
      options = [];
    } finally {
      loaded = true;
    }
  }

  $effect(() => {
    fetchOptions();
  });
</script>

<select
  {id}
  bind:value
  {disabled}
  class="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {hasError ? 'border-red-400' : 'border-neutral-200'}"
>
  <option value="">{loaded ? "Select employee..." : "Loading..."}</option>
  {#each options as emp (emp.id)}
    <option value={String(emp.id)}>{emp.employee_id} — {emp.full_name}</option>
  {/each}
</select>
