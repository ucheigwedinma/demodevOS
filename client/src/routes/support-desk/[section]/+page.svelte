<script lang="ts">
  import SupportDeskSection from "$lib/components/support-desk/SupportDeskSection.svelte";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
</script>

<SupportDeskSection
  title={data.section.title}
  description={data.section.description}
  focusAreas={data.section.focusAreas}
  operatingControls={data.section.operatingControls}
  implementationNote={data.section.implementationNote}
/>
