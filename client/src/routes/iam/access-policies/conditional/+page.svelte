<script lang="ts">
  import AccessPolicyList from "$lib/components/AccessPolicyList.svelte";
  import RoadmapNotice from "$lib/components/RoadmapNotice.svelte";
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Conditional Access</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Multi-condition policies — combine IP, time, location, device, MFA, and role checks into a
      single policy. The kind-specific pages (IP, Time, Location, Device, Session) cover the most
      common single-condition cases; conditional access composes those.
    </p>
  </div>

  <AccessPolicyList kind="conditional" />

  <RoadmapNotice
    cluster="Cluster 4 — Access Policies"
    summary="A multi-condition rule builder UI is the next iteration. The data model already supports unlimited conditions per policy; this page lists existing multi-condition rules and is the pivot into the upcoming builder."
    will={[
      "Add 2+ conditions to a single policy via a guided builder",
      "Choose AND vs OR aggregation across conditions",
      "Preview the matching subset of users / requests before enabling",
      "Surface a structured DSL for power users (JSON or rule-language)",
    ]}
    note="For now, multi-condition policies can be created via the API directly (POST /api/iam/access-policies/ with multiple conditions in the payload) and listed on this page. The single-condition kind pages cover ~80% of common policy use cases."
  />
</div>
