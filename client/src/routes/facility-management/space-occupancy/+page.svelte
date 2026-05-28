<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse } from "$lib/types";

  type OccupancyTab = "spaces" | "allocations" | "bookings" | "tenants";
  type SpaceType = "desk" | "room" | "meeting_room" | "tenant_suite" | "hot_desk" | "storage" | "other";
  type SpaceStatus = "active" | "maintenance" | "inactive";
  type AllocationType = "employee" | "department" | "tenant";
  type AllocationStatus = "pending" | "active" | "ending_soon" | "ended" | "cancelled";
  type BookingStatus = "requested" | "confirmed" | "checked_in" | "completed" | "cancelled" | "no_show" | "rejected";
  type TenantStatus = "pending_move_in" | "active" | "moved_out" | "inactive";

  interface FacilityLookupItem {
    id: number;
    facility_code: string;
    property_name: string;
  }

  interface SpaceProfileListItem {
    id: number;
    facility_space: number;
    facility: number;
    facility_code: string;
    zone_code: string;
    zone_name: string;
    unit_number: string;
    space_label: string;
    space_type: SpaceType;
    space_type_display: string;
    capacity: number;
    is_bookable: boolean;
    booking_requires_approval: boolean;
    requires_check_in: boolean;
    default_booking_duration_minutes: number;
    status: SpaceStatus;
    status_display: string;
    active_allocation_count: number;
    active_booking_count: number;
    current_occupancy: number;
    vacancy_state: string;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface DepartmentLookupItem {
    id: number;
    label: string;
    division_name: string;
  }

  interface UserLookupItem {
    id: number;
    label: string;
    email: string;
  }

  interface CustomerLookupItem {
    id: number;
    label: string;
    email: string;
    phone: string;
  }

  interface ContactLookupItem {
    id: number;
    label: string;
    entity_type: string;
    customer: number | null;
    customer_name: string;
    email: string;
    phone: string;
  }

  interface SpaceAllocationListItem {
    id: number;
    facility_space: number;
    facility: number;
    facility_code: string;
    zone_code: string;
    unit_number: string;
    space_label: string;
    allocation_type: AllocationType;
    allocation_type_display: string;
    status: AllocationStatus;
    status_display: string;
    employee: number | null;
    employee_name: string;
    department: number | null;
    department_name: string;
    tenant_customer: number | null;
    tenant_contact_account: number | null;
    tenant_name: string;
    occupant_label: string;
    occupant_count: number;
    start_date: string;
    end_date: string | null;
    allocated_by: number | null;
    released_at: string | null;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface SpaceBookingListItem {
    id: number;
    facility_space: number;
    facility: number;
    facility_code: string;
    zone_code: string;
    unit_number: string;
    space_label: string;
    title: string;
    purpose: string;
    requested_by: number | null;
    requested_by_name: string;
    approved_by: number | null;
    approved_by_name: string;
    start_at: string;
    end_at: string;
    attendee_count: number;
    status: BookingStatus;
    status_display: string;
    checked_in_at: string | null;
    checked_out_at: string | null;
    cancelled_at: string | null;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface TenantProfileListItem {
    id: number;
    customer: number | null;
    customer_name: string;
    contact_account: number | null;
    contact_account_name: string;
    primary_user: number | null;
    property: number | null;
    property_name: string;
    unit: number | null;
    unit_number: string;
    facility: number | null;
    facility_code: string;
    facility_space: number | null;
    space_label: string;
    tenant_type: string;
    tenant_type_display: string;
    status: TenantStatus;
    status_display: string;
    display_name: string;
    resolved_display_name: string;
    lease_start_date: string | null;
    lease_end_date: string | null;
    move_in_date: string | null;
    move_out_date: string | null;
    occupant_count: number;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface TenantWatchItem {
    id: number;
    display_name: string;
    status: TenantStatus;
    facility_code: string;
    space_label: string;
    unit_number: string;
    lease_end_date: string | null;
    occupant_count: number;
  }

  interface SpaceOccupancyOverview {
    generated_at: string;
    kpis: {
      total_spaces: number;
      active_spaces: number;
      occupied_spaces: number;
      vacant_spaces: number;
      occupancy_rate: number;
      vacancy_rate: number;
      bookable_spaces: number;
      active_bookings: number;
      live_bookings: number;
      tenant_allocations: number;
      employee_allocations: number;
      department_allocations: number;
      tenant_profiles_active: number;
      occupancy_capacity_used: number;
      occupancy_capacity_total: number;
    };
    space_type_breakdown: Array<{ space_type: string; count: number }>;
    allocation_status_breakdown: Array<{ status: string; count: number }>;
    vacancy_watchlist: SpaceProfileListItem[];
    allocation_watchlist: SpaceAllocationListItem[];
    booking_watchlist: SpaceBookingListItem[];
    tenant_watchlist: TenantWatchItem[];
    upcoming_bookings_count: number;
  }

  interface WorkflowSyncResult {
    space_profiles_synced: number;
    allocations_synced: number;
    allocations_ended: number;
    tenant_profiles_synced: number;
    inventory_updates: number;
    bookings_synced: number;
    bookings_completed: number;
    bookings_no_show: number;
  }

  interface SpaceOccupancyLookupsResponse {
    users: UserLookupItem[];
    facilities: FacilityLookupItem[];
    spaces: SpaceProfileListItem[];
    departments: DepartmentLookupItem[];
    customers: CustomerLookupItem[];
    contact_accounts: ContactLookupItem[];
    tenant_profiles: Array<{
      id: number;
      display_name: string;
      status: TenantStatus;
      facility_code: string;
      space_label: string;
      unit_number: string;
    }>;
  }

  const tabs: { key: OccupancyTab; label: string }[] = [
    { key: "spaces", label: "Space Allocation" },
    { key: "allocations", label: "Occupancy Tracking" },
    { key: "bookings", label: "Desk / Room Booking" },
    { key: "tenants", label: "Tenant Allocation" },
  ];

  const spaceTypeOptions: { value: SpaceType; label: string }[] = [
    { value: "meeting_room", label: "Meeting Room" },
    { value: "room", label: "Room" },
    { value: "desk", label: "Desk" },
    { value: "hot_desk", label: "Hot Desk" },
    { value: "tenant_suite", label: "Tenant Suite" },
    { value: "storage", label: "Storage" },
    { value: "other", label: "Other" },
  ];

  const spaceStatusOptions: { value: SpaceStatus; label: string }[] = [
    { value: "active", label: "Active" },
    { value: "maintenance", label: "Maintenance" },
    { value: "inactive", label: "Inactive" },
  ];

  const allocationTypeOptions: { value: AllocationType; label: string }[] = [
    { value: "employee", label: "Employee" },
    { value: "department", label: "Department" },
    { value: "tenant", label: "Tenant" },
  ];

  let activeTab = $state<OccupancyTab>("spaces");
  let loading = $state(true);
  let refreshing = $state(false);
  let syncingWorkflows = $state(false);

  let overview = $state<SpaceOccupancyOverview | null>(null);
  let spaceProfiles = $state<SpaceProfileListItem[]>([]);
  let allocations = $state<SpaceAllocationListItem[]>([]);
  let bookings = $state<SpaceBookingListItem[]>([]);
  let tenantProfiles = $state<TenantProfileListItem[]>([]);

  let usersLookup = $state<UserLookupItem[]>([]);
  let facilitiesLookup = $state<FacilityLookupItem[]>([]);
  let spacesLookup = $state<SpaceProfileListItem[]>([]);
  let departmentsLookup = $state<DepartmentLookupItem[]>([]);
  let customersLookup = $state<CustomerLookupItem[]>([]);
  let contactAccountsLookup = $state<ContactLookupItem[]>([]);

  let spaceSearch = $state("");
  let spaceFacilityFilter = $state("");
  let spaceStatusFilter = $state("");

  let allocationSearch = $state("");
  let allocationFacilityFilter = $state("");
  let allocationStatusFilter = $state("");
  let allocationTypeFilter = $state("");

  let bookingSearch = $state("");
  let bookingFacilityFilter = $state("");
  let bookingStatusFilter = $state("");

  let tenantSearch = $state("");
  let tenantStatusFilter = $state("");

  let showSpaceDrawer = $state(false);
  let showAllocationDrawer = $state(false);
  let showBookingDrawer = $state(false);

  let spaceSaving = $state(false);
  let allocationSaving = $state(false);
  let bookingSaving = $state(false);
  let releasingAllocationId = $state<number | null>(null);
  let bookingActionId = $state<number | null>(null);

  let spaceForm = $state({
    facility: "",
    facility_space: "",
    space_type: "room" as SpaceType,
    capacity: "1",
    is_bookable: false,
    booking_requires_approval: false,
    requires_check_in: false,
    default_booking_duration_minutes: "60",
    status: "active" as SpaceStatus,
    notes: "",
  });

  let allocationForm = $state({
    facility: "",
    facility_space: "",
    allocation_type: "employee" as AllocationType,
    employee: "",
    department: "",
    tenant_customer: "",
    tenant_contact_account: "",
    occupant_count: "1",
    start_date: "",
    end_date: "",
    notes: "",
  });

  let bookingForm = $state({
    facility: "",
    facility_space: "",
    title: "",
    purpose: "",
    start_at: "",
    end_at: "",
    attendee_count: "1",
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillSpace() {
    const types: SpaceType[] = ["room", "desk", "workstation", "meeting_room", "common_area", "parking", "storage", "other"];
    spaceForm.space_type = types[Math.floor(Math.random() * types.length)];
    spaceForm.capacity = String(Math.floor(Math.random() * 20) + 1);
    spaceForm.is_bookable = Math.random() > 0.3;
    spaceForm.booking_requires_approval = Math.random() > 0.5;
    spaceForm.requires_check_in = Math.random() > 0.6;
    spaceForm.default_booking_duration_minutes = ["30", "60", "90", "120"][Math.floor(Math.random() * 4)];
    spaceForm.status = "active";
    spaceForm.notes = "Auto-configured space for development testing.";
    if (facilitiesLookup.length > 0 && !spaceForm.facility) spaceForm.facility = String(facilitiesLookup[0].id);
    const filtered = spacesLookup.filter((s) => String(s.facility) === spaceForm.facility);
    if (filtered.length > 0 && !spaceForm.facility_space) spaceForm.facility_space = String(filtered[0].facility_space);
  }

  function devFillAllocation() {
    const today = new Date().toISOString().slice(0, 10);
    const endDate = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const types: AllocationType[] = ["employee", "department", "tenant"];
    allocationForm.allocation_type = types[Math.floor(Math.random() * types.length)];
    allocationForm.occupant_count = String(Math.floor(Math.random() * 5) + 1);
    allocationForm.start_date = today;
    allocationForm.end_date = endDate;
    allocationForm.notes = "Auto-allocated for development testing.";
    if (facilitiesLookup.length > 0 && !allocationForm.facility) allocationForm.facility = String(facilitiesLookup[0].id);
    if (departmentsLookup.length > 0 && !allocationForm.department) allocationForm.department = String(departmentsLookup[0].id);
    if (customersLookup.length > 0 && !allocationForm.tenant_customer) allocationForm.tenant_customer = String(customersLookup[0].id);
  }

  function devFillBooking() {
    const now = new Date();
    const start = new Date(now.getTime() + 2 * 60 * 60 * 1000);
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    const titles = ["Team standup meeting", "Client presentation", "Technical review session", "HR orientation", "Sprint retrospective", "Budget review"];
    const purposes = ["Weekly alignment", "New client onboarding", "Architecture deep-dive", "New hire walkthrough", "Process improvement", "Q2 forecast review"];
    const idx = Math.floor(Math.random() * titles.length);
    bookingForm.title = titles[idx];
    bookingForm.purpose = purposes[idx];
    bookingForm.start_at = start.toISOString().slice(0, 16);
    bookingForm.end_at = end.toISOString().slice(0, 16);
    bookingForm.attendee_count = String(Math.floor(Math.random() * 15) + 2);
    bookingForm.notes = "Auto-booked for development testing.";
    if (facilitiesLookup.length > 0 && !bookingForm.facility) bookingForm.facility = String(facilitiesLookup[0].id);
  }

  function resetSpaceForm(profile?: SpaceProfileListItem) {
    spaceForm.facility = profile ? String(profile.facility) : "";
    spaceForm.facility_space = profile ? String(profile.facility_space) : "";
    spaceForm.space_type = profile?.space_type ?? "room";
    spaceForm.capacity = String(profile?.capacity ?? 1);
    spaceForm.is_bookable = profile?.is_bookable ?? false;
    spaceForm.booking_requires_approval = profile?.booking_requires_approval ?? false;
    spaceForm.requires_check_in = profile?.requires_check_in ?? false;
    spaceForm.default_booking_duration_minutes = String(profile?.default_booking_duration_minutes ?? 60);
    spaceForm.status = profile?.status ?? "active";
    spaceForm.notes = profile?.notes ?? "";
  }

  function resetAllocationForm(prefill?: { facility?: number; facility_space?: number; allocation_type?: AllocationType }) {
    allocationForm.facility = prefill?.facility ? String(prefill.facility) : "";
    allocationForm.facility_space = prefill?.facility_space ? String(prefill.facility_space) : "";
    allocationForm.allocation_type = prefill?.allocation_type ?? "employee";
    allocationForm.employee = "";
    allocationForm.department = "";
    allocationForm.tenant_customer = "";
    allocationForm.tenant_contact_account = "";
    allocationForm.occupant_count = "1";
    allocationForm.start_date = new Date().toISOString().slice(0, 10);
    allocationForm.end_date = "";
    allocationForm.notes = "";
  }

  function resetBookingForm(prefill?: { facility?: number; facility_space?: number }) {
    const start = new Date();
    start.setHours(start.getHours() + 1, 0, 0, 0);
    const end = new Date(start);
    end.setHours(end.getHours() + 1);

    bookingForm.facility = prefill?.facility ? String(prefill.facility) : "";
    bookingForm.facility_space = prefill?.facility_space ? String(prefill.facility_space) : "";
    bookingForm.title = "";
    bookingForm.purpose = "";
    bookingForm.start_at = toDateTimeLocal(start.toISOString());
    bookingForm.end_at = toDateTimeLocal(end.toISOString());
    bookingForm.attendee_count = "1";
    bookingForm.notes = "";
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function fmtDateTime(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function fmtLabel(value: string): string {
    return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function fmtPercent(value: number): string {
    return `${Number(value || 0).toFixed(1)}%`;
  }

  function parseApiMessage(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data.detail === "string") return error.data.detail;
      const fieldMessage = Object.values(error.fieldErrors).flat().join(" ");
      if (fieldMessage) return fieldMessage;
    }
    return fallback;
  }

  function toDateTimeLocal(value: string | null | undefined): string {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const offset = date.getTimezoneOffset();
    const local = new Date(date.getTime() - offset * 60 * 1000);
    return local.toISOString().slice(0, 16);
  }

  function toIsoDateTime(value: string): string | null {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString();
  }

  function badgeTone(value: string): string {
    switch (value) {
      case "active":
      case "confirmed":
      case "checked_in":
      case "completed":
      case "full":
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
      case "ending_soon":
      case "requested":
      case "partially_occupied":
      case "maintenance":
        return "border-amber-200 bg-amber-50 text-amber-700";
      case "pending":
      case "room":
      case "meeting_room":
      case "desk":
        return "border-sky-200 bg-sky-50 text-sky-700";
      case "cancelled":
      case "inactive":
      case "ended":
      case "no_show":
      case "rejected":
      case "offline":
        return "border-rose-200 bg-rose-50 text-rose-700";
      default:
        return "border-neutral-200 bg-neutral-100 text-neutral-700";
    }
  }

  const spacesMap = $derived.by(() => {
    const entries = spacesLookup.map((item) => [item.facility_space, item] as const);
    return new Map(entries);
  });

  const contactsMap = $derived.by(() => {
    const entries = contactAccountsLookup.map((item) => [item.id, item] as const);
    return new Map(entries);
  });

  const filteredSpaceProfiles = $derived.by(() => {
    const term = spaceSearch.trim().toLowerCase();
    return spaceProfiles.filter((item) => {
      const matchesSearch = !term || [
        item.space_label,
        item.unit_number,
        item.facility_code,
        item.zone_name,
        item.zone_code,
        item.space_type_display,
      ].some((value) => value.toLowerCase().includes(term));
      const matchesFacility = !spaceFacilityFilter || String(item.facility) === spaceFacilityFilter;
      const matchesStatus = !spaceStatusFilter || item.status === spaceStatusFilter;
      return matchesSearch && matchesFacility && matchesStatus;
    });
  });

  const filteredAllocations = $derived.by(() => {
    const term = allocationSearch.trim().toLowerCase();
    return allocations.filter((item) => {
      const matchesSearch = !term || [
        item.occupant_label,
        item.employee_name,
        item.department_name,
        item.tenant_name,
        item.space_label,
        item.unit_number,
        item.facility_code,
      ].some((value) => value.toLowerCase().includes(term));
      const matchesFacility = !allocationFacilityFilter || String(item.facility) === allocationFacilityFilter;
      const matchesStatus = !allocationStatusFilter || item.status === allocationStatusFilter;
      const matchesType = !allocationTypeFilter || item.allocation_type === allocationTypeFilter;
      return matchesSearch && matchesFacility && matchesStatus && matchesType;
    });
  });

  const filteredBookings = $derived.by(() => {
    const term = bookingSearch.trim().toLowerCase();
    return bookings.filter((item) => {
      const matchesSearch = !term || [
        item.title,
        item.purpose,
        item.space_label,
        item.unit_number,
        item.facility_code,
        item.requested_by_name,
      ].some((value) => value.toLowerCase().includes(term));
      const matchesFacility = !bookingFacilityFilter || String(item.facility) === bookingFacilityFilter;
      const matchesStatus = !bookingStatusFilter || item.status === bookingStatusFilter;
      return matchesSearch && matchesFacility && matchesStatus;
    });
  });

  const filteredTenantProfiles = $derived.by(() => {
    const term = tenantSearch.trim().toLowerCase();
    return tenantProfiles.filter((item) => {
      const matchesSearch = !term || [
        item.resolved_display_name,
        item.customer_name,
        item.contact_account_name,
        item.space_label,
        item.unit_number,
        item.facility_code,
        item.property_name,
      ].some((value) => value.toLowerCase().includes(term));
      const matchesStatus = !tenantStatusFilter || item.status === tenantStatusFilter;
      return matchesSearch && matchesStatus;
    });
  });

  function spacesForFacility(facilityId: string, options: { bookableOnly?: boolean } = {}): SpaceProfileListItem[] {
    const matches = spacesLookup.filter((item) => !facilityId || String(item.facility) === facilityId);
    return options.bookableOnly ? matches.filter((item) => item.is_bookable) : matches;
  }

  async function fetchOverview() {
    overview = await api.get<SpaceOccupancyOverview>("/facility-management/space-occupancy/overview/");
  }

  async function fetchSpaceProfiles() {
    const response = await api.get<PaginatedResponse<SpaceProfileListItem>>("/facility-management/space-occupancy/profiles/", { page_size: "200" });
    spaceProfiles = response.results;
  }

  async function fetchAllocations() {
    const response = await api.get<PaginatedResponse<SpaceAllocationListItem>>("/facility-management/space-occupancy/allocations/", { page_size: "200" });
    allocations = response.results;
  }

  async function fetchBookings() {
    const response = await api.get<PaginatedResponse<SpaceBookingListItem>>("/facility-management/space-occupancy/bookings/", { page_size: "200" });
    bookings = response.results;
  }

  async function fetchTenantProfiles() {
    const response = await api.get<PaginatedResponse<TenantProfileListItem>>("/tenants/profiles/", { page_size: "200" });
    tenantProfiles = response.results;
  }

  async function fetchLookups() {
    const response = await api.get<SpaceOccupancyLookupsResponse>("/facility-management/space-occupancy/lookups/");
    usersLookup = response.users;
    facilitiesLookup = response.facilities;
    spacesLookup = response.spaces;
    departmentsLookup = response.departments;
    customersLookup = response.customers;
    contactAccountsLookup = response.contact_accounts;
  }

  async function syncWorkflows(options: { silent?: boolean } = {}): Promise<WorkflowSyncResult | null> {
    syncingWorkflows = true;
    try {
      const result = await api.post<WorkflowSyncResult>("/facility-management/space-occupancy/sync/", {});
      if (!options.silent) {
        toast.success(
          "Space workflows synced",
          [
            `${result.allocations_synced} allocations refreshed`,
            `${result.tenant_profiles_synced} tenant profiles synced`,
            `${result.bookings_synced} bookings updated`,
          ].join(" • "),
        );
      }
      return result;
    } catch (error) {
      if (!options.silent) {
        toast.error("Workflow run failed", parseApiMessage(error, "The occupancy workflow engine could not be executed."));
      }
      return null;
    } finally {
      syncingWorkflows = false;
    }
  }

  async function refreshAll() {
    if (!loading) refreshing = true;
    try {
      await Promise.all([
        fetchOverview(),
        fetchSpaceProfiles(),
        fetchAllocations(),
        fetchBookings(),
        fetchTenantProfiles(),
        fetchLookups(),
      ]);
    } catch {
      toast.error("Load failed", "Could not load space and occupancy management.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function handleRunWorkflows() {
    await syncWorkflows();
    await refreshAll();
  }

  function openSpaceDrawer(profile?: SpaceProfileListItem) {
    resetSpaceForm(profile);
    showSpaceDrawer = true;
    void fetchLookups();
  }

  function closeSpaceDrawer() {
    showSpaceDrawer = false;
    resetSpaceForm();
  }

  function openAllocationDrawer(prefill?: { facility?: number; facility_space?: number; allocation_type?: AllocationType }) {
    resetAllocationForm(prefill);
    showAllocationDrawer = true;
    void fetchLookups();
  }

  function closeAllocationDrawer() {
    showAllocationDrawer = false;
    resetAllocationForm();
  }

  function openBookingDrawer(prefill?: { facility?: number; facility_space?: number }) {
    resetBookingForm(prefill);
    showBookingDrawer = true;
    void fetchLookups();
  }

  function closeBookingDrawer() {
    showBookingDrawer = false;
    resetBookingForm();
  }

  async function handleSpaceSubmit(event: Event) {
    event.preventDefault();
    if (!spaceForm.facility_space) {
      toast.error("Missing data", "Choose a mapped room or space.");
      return;
    }

    spaceSaving = true;
    try {
      await api.post("/facility-management/space-occupancy/profiles/", {
        facility_space: Number(spaceForm.facility_space),
        space_type: spaceForm.space_type,
        capacity: Number(spaceForm.capacity || 1),
        is_bookable: spaceForm.is_bookable,
        booking_requires_approval: spaceForm.booking_requires_approval,
        requires_check_in: spaceForm.requires_check_in,
        default_booking_duration_minutes: Number(spaceForm.default_booking_duration_minutes || 60),
        status: spaceForm.status,
        notes: spaceForm.notes.trim(),
      });
      toast.success("Space profile saved", "Space allocation and booking settings have been updated.");
      closeSpaceDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the space profile."));
    } finally {
      spaceSaving = false;
    }
  }

  async function handleAllocationSubmit(event: Event) {
    event.preventDefault();
    if (!allocationForm.facility_space) {
      toast.error("Missing data", "Choose a mapped room or space.");
      return;
    }
    if (!allocationForm.start_date) {
      toast.error("Missing data", "Allocation start date is required.");
      return;
    }

    if (allocationForm.allocation_type === "employee" && !allocationForm.employee) {
      toast.error("Missing data", "Select an employee for this allocation.");
      return;
    }
    if (allocationForm.allocation_type === "department" && !allocationForm.department) {
      toast.error("Missing data", "Select a department for this allocation.");
      return;
    }
    if (allocationForm.allocation_type === "tenant" && !allocationForm.tenant_customer && !allocationForm.tenant_contact_account) {
      toast.error("Missing data", "Select a customer or contact account for the tenant allocation.");
      return;
    }

    allocationSaving = true;
    try {
      await api.post("/facility-management/space-occupancy/allocations/", {
        facility_space: Number(allocationForm.facility_space),
        allocation_type: allocationForm.allocation_type,
        employee:
          allocationForm.allocation_type === "employee" && allocationForm.employee
            ? Number(allocationForm.employee)
            : null,
        department:
          allocationForm.allocation_type === "department" && allocationForm.department
            ? Number(allocationForm.department)
            : null,
        tenant_customer:
          allocationForm.allocation_type === "tenant" && allocationForm.tenant_customer
            ? Number(allocationForm.tenant_customer)
            : null,
        tenant_contact_account:
          allocationForm.allocation_type === "tenant" && allocationForm.tenant_contact_account
            ? Number(allocationForm.tenant_contact_account)
            : null,
        occupant_count: Number(allocationForm.occupant_count || 1),
        start_date: allocationForm.start_date,
        end_date: allocationForm.end_date || null,
        notes: allocationForm.notes.trim(),
      });
      toast.success("Space allocated", "Occupancy tracking and tenant sync automation were applied.");
      closeAllocationDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Create failed", parseApiMessage(error, "Could not allocate the selected space."));
    } finally {
      allocationSaving = false;
    }
  }

  async function handleBookingSubmit(event: Event) {
    event.preventDefault();
    if (!bookingForm.facility_space) {
      toast.error("Missing data", "Choose a bookable room or desk.");
      return;
    }
    if (!bookingForm.title.trim()) {
      toast.error("Missing data", "Booking title is required.");
      return;
    }
    if (!bookingForm.start_at || !bookingForm.end_at) {
      toast.error("Missing data", "Start and end times are required.");
      return;
    }

    bookingSaving = true;
    try {
      await api.post("/facility-management/space-occupancy/bookings/", {
        facility_space: Number(bookingForm.facility_space),
        title: bookingForm.title.trim(),
        purpose: bookingForm.purpose.trim(),
        start_at: toIsoDateTime(bookingForm.start_at),
        end_at: toIsoDateTime(bookingForm.end_at),
        attendee_count: Number(bookingForm.attendee_count || 1),
        notes: bookingForm.notes.trim(),
      });
      toast.success("Booking created", "Booking workflow automation and occupancy checks are active.");
      closeBookingDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Create failed", parseApiMessage(error, "Could not create the booking."));
    } finally {
      bookingSaving = false;
    }
  }

  async function handleReleaseAllocation(item: SpaceAllocationListItem) {
    releasingAllocationId = item.id;
    try {
      await api.post(`/facility-management/space-occupancy/allocations/${item.id}/release/`, {});
      toast.success("Allocation released", `${item.occupant_label} has been removed from ${item.space_label || item.unit_number}.`);
      await refreshAll();
    } catch (error) {
      toast.error("Release failed", parseApiMessage(error, "Could not release the selected allocation."));
    } finally {
      releasingAllocationId = null;
    }
  }

  async function handleBookingAction(item: SpaceBookingListItem, action: "confirm" | "cancel" | "check-in") {
    bookingActionId = item.id;
    try {
      await api.post(`/facility-management/space-occupancy/bookings/${item.id}/${action}/`, {});
      toast.success(
        "Booking updated",
        action === "confirm"
          ? `${item.title} has been confirmed.`
          : action === "cancel"
            ? `${item.title} has been cancelled.`
            : `${item.title} has been checked in.`,
      );
      await refreshAll();
    } catch (error) {
      toast.error("Update failed", parseApiMessage(error, "Could not update the selected booking."));
    } finally {
      bookingActionId = null;
    }
  }

  $effect(() => {
    const spaceId = Number(spaceForm.facility_space || 0);
    if (!spaceId) return;
    const selected = spacesMap.get(spaceId);
    if (selected && !spaceForm.facility) {
      spaceForm.facility = String(selected.facility);
    }
  });

  $effect(() => {
    const spaceId = Number(allocationForm.facility_space || 0);
    if (!spaceId) return;
    const selected = spacesMap.get(spaceId);
    if (selected && !allocationForm.facility) {
      allocationForm.facility = String(selected.facility);
    }
  });

  $effect(() => {
    const spaceId = Number(bookingForm.facility_space || 0);
    if (!spaceId) return;
    const selected = spacesMap.get(spaceId);
    if (selected && !bookingForm.facility) {
      bookingForm.facility = String(selected.facility);
    }
  });

  $effect(() => {
    if (allocationForm.allocation_type !== "tenant") return;
    const contactId = Number(allocationForm.tenant_contact_account || 0);
    if (!contactId || allocationForm.tenant_customer) return;
    const contact = contactsMap.get(contactId);
    if (contact?.customer) {
      allocationForm.tenant_customer = String(contact.customer);
    }
  });

  $effect(() => {
    const spaceId = Number(bookingForm.facility_space || 0);
    if (!spaceId || !bookingForm.start_at || bookingForm.end_at) return;
    const selected = spacesMap.get(spaceId);
    if (!selected) return;
    const start = new Date(bookingForm.start_at);
    if (Number.isNaN(start.getTime())) return;
    const end = new Date(start);
    end.setMinutes(end.getMinutes() + selected.default_booking_duration_minutes);
    bookingForm.end_at = toDateTimeLocal(end.toISOString());
  });

  void refreshAll();
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">Facility Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Space & Occupancy Management</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Allocate workspaces, monitor occupancy, analyze vacancy, manage bookings, and sync tenant allocations into the Tenants module.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>
      {/if}
    </div>

    <div class="flex flex-wrap items-center gap-2 lg:ml-auto lg:justify-end">
      <button
        type="button"
        onclick={handleRunWorkflows}
        disabled={syncingWorkflows || loading}
        class="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {syncingWorkflows ? "Running Workflows..." : "Run Workflows"}
      </button>
      <button
        type="button"
        onclick={refreshAll}
        disabled={refreshing}
        class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={refreshing ? "Refreshing space and occupancy management" : "Refresh space and occupancy management"}
        title={refreshing ? "Refreshing space and occupancy management" : "Refresh space and occupancy management"}
      >
        <svg
          class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="1.8"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003"
          />
        </svg>
      </button>
    </div>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">
      Loading space and occupancy management...
    </div>
  {:else if !overview}
    <div class="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      Space and occupancy overview is unavailable right now.
    </div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
      <section class="rounded-2xl border border-sky-200 bg-sky-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-sky-700">Occupancy Rate</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{fmtPercent(overview.kpis.occupancy_rate)}</p>
        <p class="mt-1 text-xs text-sky-800">
          {overview.kpis.occupancy_capacity_used} / {overview.kpis.occupancy_capacity_total} seats in use
        </p>
      </section>
      <section class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-emerald-700">Occupied Spaces</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.occupied_spaces}</p>
        <p class="mt-1 text-xs text-emerald-800">Active spaces: {overview.kpis.active_spaces}</p>
      </section>
      <section class="rounded-2xl border border-amber-200 bg-amber-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-amber-700">Vacancy Rate</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{fmtPercent(overview.kpis.vacancy_rate)}</p>
        <p class="mt-1 text-xs text-amber-800">Vacant spaces: {overview.kpis.vacant_spaces}</p>
      </section>
      <section class="rounded-2xl border border-violet-200 bg-violet-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-violet-700">Bookable Spaces</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.bookable_spaces}</p>
        <p class="mt-1 text-xs text-violet-800">
          Live bookings: {overview.kpis.live_bookings} • Upcoming: {overview.upcoming_bookings_count}
        </p>
      </section>
      <section class="rounded-2xl border border-rose-200 bg-rose-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-rose-700">Tenant Allocation</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.tenant_allocations}</p>
        <p class="mt-1 text-xs text-rose-800">Active tenant profiles: {overview.kpis.tenant_profiles_active}</p>
      </section>
      <section class="rounded-2xl border border-orange-200 bg-orange-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-orange-700">Workplace Allocation</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.employee_allocations + overview.kpis.department_allocations}</p>
        <p class="mt-1 text-xs text-orange-800">
          Employees: {overview.kpis.employee_allocations} • Departments: {overview.kpis.department_allocations}
        </p>
      </section>
    </div>

    <div class="grid gap-4 xl:grid-cols-3">
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Vacancy Watchlist</h2>
        <div class="mt-4 space-y-3">
          {#if overview.vacancy_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No vacant active spaces right now.</p>
          {:else}
            {#each overview.vacancy_watchlist as item}
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-medium text-neutral-900">{item.space_label || item.unit_number}</p>
                    <p class="mt-1 text-xs text-neutral-500">
                      {item.facility_code} • {item.zone_name} • {item.space_type_display}
                    </p>
                  </div>
                  <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.vacancy_state)}`}>
                    {fmtLabel(item.vacancy_state)}
                  </span>
                </div>
                <p class="mt-2 text-xs text-neutral-500">Capacity {item.capacity} • Bookable {item.is_bookable ? "Yes" : "No"}</p>
              </div>
            {/each}
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Allocation Watchlist</h2>
        <div class="mt-4 space-y-3">
          {#if overview.allocation_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No ending-soon allocations at the moment.</p>
          {:else}
            {#each overview.allocation_watchlist as item}
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-medium text-neutral-900">{item.occupant_label}</p>
                    <p class="mt-1 text-xs text-neutral-500">
                      {item.space_label || item.unit_number} • {item.facility_code} • {item.allocation_type_display}
                    </p>
                  </div>
                  <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>
                    {fmtLabel(item.status)}
                  </span>
                </div>
                <p class="mt-2 text-xs text-neutral-500">Ends {fmtDate(item.end_date)} • {item.occupant_count} occupant(s)</p>
              </div>
            {/each}
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Booking Feed</h2>
        <div class="mt-4 space-y-3">
          {#if overview.booking_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No active or upcoming bookings right now.</p>
          {:else}
            {#each overview.booking_watchlist as item}
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-medium text-neutral-900">{item.title}</p>
                    <p class="mt-1 text-xs text-neutral-500">
                      {item.space_label || item.unit_number} • {item.facility_code}
                    </p>
                  </div>
                  <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>
                    {fmtLabel(item.status)}
                  </span>
                </div>
                <p class="mt-2 text-xs text-neutral-500">{fmtDateTime(item.start_at)} - {fmtDateTime(item.end_at)}</p>
              </div>
            {/each}
          {/if}
        </div>
      </section>
    </div>

    <div class="rounded-2xl border border-neutral-200 bg-white p-2">
      <nav class="flex flex-wrap gap-2">
        {#each tabs as tab}
          <button
            type="button"
            onclick={() => (activeTab = tab.key)}
            class={`rounded-xl px-4 py-2 text-sm font-medium transition ${activeTab === tab.key ? "bg-neutral-900 text-white" : "bg-white text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"}`}
          >
            {tab.label}
          </button>
        {/each}
      </nav>
    </div>

    {#if activeTab === "spaces"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-900">Space Allocation</h2>
            <p class="mt-1 text-sm text-neutral-500">Configure capacity, booking rules, and availability for mapped spaces.</p>
          </div>
          <button
            type="button"
            onclick={() => openSpaceDrawer()}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Configure Space
          </button>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-3">
          <input bind:value={spaceSearch} class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Search space, unit, zone..." />
          <select bind:value={spaceFacilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All facilities</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
          <select bind:value={spaceStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All statuses</option>
            {#each spaceStatusOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div class="mt-5 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50">
              <tr class="text-left text-xs uppercase tracking-wide text-neutral-500">
                <th class="px-4 py-3">Space</th>
                <th class="px-4 py-3">Type</th>
                <th class="px-4 py-3">Capacity</th>
                <th class="px-4 py-3">Vacancy</th>
                <th class="px-4 py-3">Booking</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200">
              {#if filteredSpaceProfiles.length === 0}
                <tr>
                  <td colspan="7" class="px-4 py-10 text-center text-sm text-neutral-500">No spaces match the current filters.</td>
                </tr>
              {:else}
                {#each filteredSpaceProfiles as item (item.id)}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <p class="font-medium text-neutral-900">{item.space_label || item.unit_number}</p>
                      <p class="mt-1 text-xs text-neutral-500">{item.facility_code} • {item.zone_name} • Unit {item.unit_number}</p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.space_type)}`}>{item.space_type_display}</span>
                    </td>
                    <td class="px-4 py-4 text-neutral-700">
                      <p>{item.current_occupancy} / {item.capacity}</p>
                      <p class="mt-1 text-xs text-neutral-500">Allocations: {item.active_allocation_count}</p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.vacancy_state)}`}>{fmtLabel(item.vacancy_state)}</span>
                    </td>
                    <td class="px-4 py-4 text-neutral-700">
                      <p>{item.is_bookable ? "Bookable" : "Not bookable"}</p>
                      <p class="mt-1 text-xs text-neutral-500">Open bookings: {item.active_booking_count}</p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>{item.status_display}</span>
                    </td>
                    <td class="px-4 py-4">
                      <div class="flex justify-end gap-2">
                        <button type="button" onclick={() => openSpaceDrawer(item)} class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Configure</button>
                        <button type="button" onclick={() => openAllocationDrawer({ facility: item.facility, facility_space: item.facility_space })} class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Allocate</button>
                        {#if item.is_bookable}
                          <button type="button" onclick={() => openBookingDrawer({ facility: item.facility, facility_space: item.facility_space })} class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Book</button>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    {#if activeTab === "allocations"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-900">Occupancy Tracking</h2>
            <p class="mt-1 text-sm text-neutral-500">Track employee, department, and tenant occupancy with automated lifecycle status changes.</p>
          </div>
          <button
            type="button"
            onclick={() => openAllocationDrawer()}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Allocate Space
          </button>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-4">
          <input bind:value={allocationSearch} class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Search occupant, space, facility..." />
          <select bind:value={allocationFacilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All facilities</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
          <select bind:value={allocationTypeFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All allocation types</option>
            {#each allocationTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
          <select bind:value={allocationStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="active">Active</option>
            <option value="ending_soon">Ending Soon</option>
            <option value="ended">Ended</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <div class="mt-5 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50">
              <tr class="text-left text-xs uppercase tracking-wide text-neutral-500">
                <th class="px-4 py-3">Space</th>
                <th class="px-4 py-3">Occupant</th>
                <th class="px-4 py-3">Allocation</th>
                <th class="px-4 py-3">Occupants</th>
                <th class="px-4 py-3">Dates</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200">
              {#if filteredAllocations.length === 0}
                <tr>
                  <td colspan="7" class="px-4 py-10 text-center text-sm text-neutral-500">No allocations match the current filters.</td>
                </tr>
              {:else}
                {#each filteredAllocations as item (item.id)}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <p class="font-medium text-neutral-900">{item.space_label || item.unit_number}</p>
                      <p class="mt-1 text-xs text-neutral-500">{item.facility_code} • {item.zone_code} • Unit {item.unit_number}</p>
                    </td>
                    <td class="px-4 py-4">
                      <p class="font-medium text-neutral-900">{item.occupant_label}</p>
                      <p class="mt-1 text-xs text-neutral-500">
                        {item.employee_name || item.department_name || item.tenant_name || "--"}
                      </p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.allocation_type)}`}>{item.allocation_type_display}</span>
                    </td>
                    <td class="px-4 py-4 text-neutral-700">{item.occupant_count}</td>
                    <td class="px-4 py-4 text-neutral-700">
                      <p>{fmtDate(item.start_date)}</p>
                      <p class="mt-1 text-xs text-neutral-500">End: {fmtDate(item.end_date)}</p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>{item.status_display}</span>
                    </td>
                    <td class="px-4 py-4">
                      <div class="flex justify-end gap-2">
                        {#if item.status === "pending" || item.status === "active" || item.status === "ending_soon"}
                          <button
                            type="button"
                            onclick={() => handleReleaseAllocation(item)}
                            disabled={releasingAllocationId === item.id}
                            class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {releasingAllocationId === item.id ? "Releasing..." : "Release"}
                          </button>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    {#if activeTab === "bookings"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-900">Desk / Room Booking</h2>
            <p class="mt-1 text-sm text-neutral-500">Manage corporate room and desk reservations with approval, check-in, and no-show handling.</p>
          </div>
          <button
            type="button"
            onclick={() => openBookingDrawer()}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Book Space
          </button>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-3">
          <input bind:value={bookingSearch} class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Search booking, room, requester..." />
          <select bind:value={bookingFacilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All facilities</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
          <select bind:value={bookingStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All statuses</option>
            <option value="requested">Requested</option>
            <option value="confirmed">Confirmed</option>
            <option value="checked_in">Checked In</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
            <option value="no_show">No Show</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div class="mt-5 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50">
              <tr class="text-left text-xs uppercase tracking-wide text-neutral-500">
                <th class="px-4 py-3">Space</th>
                <th class="px-4 py-3">Booking</th>
                <th class="px-4 py-3">Time</th>
                <th class="px-4 py-3">Attendees</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200">
              {#if filteredBookings.length === 0}
                <tr>
                  <td colspan="6" class="px-4 py-10 text-center text-sm text-neutral-500">No bookings match the current filters.</td>
                </tr>
              {:else}
                {#each filteredBookings as item (item.id)}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <p class="font-medium text-neutral-900">{item.space_label || item.unit_number}</p>
                      <p class="mt-1 text-xs text-neutral-500">{item.facility_code} • {item.zone_code}</p>
                    </td>
                    <td class="px-4 py-4">
                      <p class="font-medium text-neutral-900">{item.title}</p>
                      <p class="mt-1 text-xs text-neutral-500">Requester: {item.requested_by_name || "--"}</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-700">
                      <p>{fmtDateTime(item.start_at)}</p>
                      <p class="mt-1 text-xs text-neutral-500">Ends {fmtDateTime(item.end_at)}</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-700">{item.attendee_count}</td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>{item.status_display}</span>
                    </td>
                    <td class="px-4 py-4">
                      <div class="flex justify-end gap-2">
                        {#if item.status === "requested"}
                          <button
                            type="button"
                            onclick={() => handleBookingAction(item, "confirm")}
                            disabled={bookingActionId === item.id}
                            class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Confirm
                          </button>
                        {/if}
                        {#if item.status === "confirmed"}
                          <button
                            type="button"
                            onclick={() => handleBookingAction(item, "check-in")}
                            disabled={bookingActionId === item.id}
                            class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Check In
                          </button>
                        {/if}
                        {#if item.status === "requested" || item.status === "confirmed" || item.status === "checked_in"}
                          <button
                            type="button"
                            onclick={() => handleBookingAction(item, "cancel")}
                            disabled={bookingActionId === item.id}
                            class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Cancel
                          </button>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    {#if activeTab === "tenants"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-900">Tenant Allocation</h2>
            <p class="mt-1 text-sm text-neutral-500">Read-only tenant occupancy view sourced from synced tenant profiles and facility allocations.</p>
          </div>
          <button
            type="button"
            onclick={() => openAllocationDrawer({ allocation_type: "tenant" })}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Allocate Tenant
          </button>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-2">
          <input bind:value={tenantSearch} class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Search tenant, suite, property..." />
          <select bind:value={tenantStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All statuses</option>
            <option value="pending_move_in">Pending Move In</option>
            <option value="active">Active</option>
            <option value="moved_out">Moved Out</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        <div class="mt-5 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50">
              <tr class="text-left text-xs uppercase tracking-wide text-neutral-500">
                <th class="px-4 py-3">Tenant</th>
                <th class="px-4 py-3">Location</th>
                <th class="px-4 py-3">Lease Window</th>
                <th class="px-4 py-3">Occupants</th>
                <th class="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200">
              {#if filteredTenantProfiles.length === 0}
                <tr>
                  <td colspan="5" class="px-4 py-10 text-center text-sm text-neutral-500">No tenant profiles match the current filters.</td>
                </tr>
              {:else}
                {#each filteredTenantProfiles as item (item.id)}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <p class="font-medium text-neutral-900">{item.resolved_display_name}</p>
                      <p class="mt-1 text-xs text-neutral-500">
                        {item.customer_name || item.contact_account_name || "--"} • {item.tenant_type_display}
                      </p>
                    </td>
                    <td class="px-4 py-4 text-neutral-700">
                      <p>{item.space_label || item.unit_number || "--"}</p>
                      <p class="mt-1 text-xs text-neutral-500">{item.facility_code || "--"} • {item.property_name || "--"}</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-700">
                      <p>{fmtDate(item.lease_start_date)}</p>
                      <p class="mt-1 text-xs text-neutral-500">Ends {fmtDate(item.lease_end_date)}</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-700">{item.occupant_count}</td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>{item.status_display}</span>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {/if}
  {/if}
</div>

{#if showSpaceDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeSpaceDrawer}
    tabindex="-1"
    aria-label="Close space drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Configure Space</h2>
        <p class="mt-1 text-xs text-neutral-500">All facility management forms stay in drawers for consistent workflow handling.</p>
      </div>
      <button
        type="button"
        onclick={closeSpaceDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close space drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="space-profile-form" class="space-y-5" onsubmit={handleSpaceSubmit}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select bind:value={spaceForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Room / Space</span>
            <select bind:value={spaceForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select room / space</option>
              {#each spacesForFacility(spaceForm.facility) as space}
                <option value={String(space.facility_space)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Space Type</span>
            <select bind:value={spaceForm.space_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each spaceTypeOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Capacity</span>
            <input type="number" min="1" bind:value={spaceForm.capacity} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Default Booking Duration (mins)</span>
            <input type="number" min="15" step="15" bind:value={spaceForm.default_booking_duration_minutes} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Status</span>
            <select bind:value={spaceForm.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each spaceStatusOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
        </section>

        <section class="grid gap-3 rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
          <label class="flex items-center gap-3 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={spaceForm.is_bookable} class="rounded border-neutral-300" />
            Enable desk / room booking
          </label>
          <label class="flex items-center gap-3 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={spaceForm.booking_requires_approval} class="rounded border-neutral-300" />
            Require manager approval before booking is confirmed
          </label>
          <label class="flex items-center gap-3 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={spaceForm.requires_check_in} class="rounded border-neutral-300" />
            Require physical or app check-in before occupancy starts
          </label>
        </section>

        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={spaceForm.notes} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Use this space for investor briefings on weekdays only."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillSpace} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeSpaceDrawer} class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">
        Cancel
      </button>
      <button
        type="submit"
        form="space-profile-form"
        disabled={spaceSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {spaceSaving ? "Saving..." : "Save Space"}
      </button>
    </div>
  </aside>
{/if}

{#if showAllocationDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeAllocationDrawer}
    tabindex="-1"
    aria-label="Close allocation drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Allocate Space</h2>
        <p class="mt-1 text-xs text-neutral-500">Create employee, department, or tenant allocations with automated occupancy and lease sync.</p>
      </div>
      <button
        type="button"
        onclick={closeAllocationDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close allocation drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="space-allocation-form" class="space-y-5" onsubmit={handleAllocationSubmit}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select bind:value={allocationForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Room / Space</span>
            <select bind:value={allocationForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select room / space</option>
              {#each spacesForFacility(allocationForm.facility) as space}
                <option value={String(space.facility_space)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Allocation Type</span>
            <select bind:value={allocationForm.allocation_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each allocationTypeOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Occupant Count</span>
            <input type="number" min="1" bind:value={allocationForm.occupant_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          {#if allocationForm.allocation_type === "employee"}
            <label class="text-sm font-medium text-neutral-700 md:col-span-2">
              <span class="mb-1.5 block">Employee</span>
              <select bind:value={allocationForm.employee} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
                <option value="">Select employee</option>
                {#each usersLookup as user}
                  <option value={String(user.id)}>{user.label}</option>
                {/each}
              </select>
            </label>
          {/if}

          {#if allocationForm.allocation_type === "department"}
            <label class="text-sm font-medium text-neutral-700 md:col-span-2">
              <span class="mb-1.5 block">Department</span>
              <select bind:value={allocationForm.department} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
                <option value="">Select department</option>
                {#each departmentsLookup as department}
                  <option value={String(department.id)}>{department.label} - {department.division_name}</option>
                {/each}
              </select>
            </label>
          {/if}

          {#if allocationForm.allocation_type === "tenant"}
            <label class="text-sm font-medium text-neutral-700">
              <span class="mb-1.5 block">Customer</span>
              <select bind:value={allocationForm.tenant_customer} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
                <option value="">Select customer</option>
                {#each customersLookup as customer}
                  <option value={String(customer.id)}>{customer.label}</option>
                {/each}
              </select>
            </label>

            <label class="text-sm font-medium text-neutral-700">
              <span class="mb-1.5 block">Contact Account</span>
              <select bind:value={allocationForm.tenant_contact_account} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
                <option value="">Select contact account</option>
                {#each contactAccountsLookup as contact}
                  <option value={String(contact.id)}>{contact.label}{contact.customer_name ? ` • ${contact.customer_name}` : ""}</option>
                {/each}
              </select>
            </label>
          {/if}

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Start Date</span>
            <input type="date" bind:value={allocationForm.start_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">End Date</span>
            <input type="date" bind:value={allocationForm.end_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>
        </section>

        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={allocationForm.notes} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Reserved for project war-room occupancy through quarter close."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillAllocation} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeAllocationDrawer} class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">
        Cancel
      </button>
      <button
        type="submit"
        form="space-allocation-form"
        disabled={allocationSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {allocationSaving ? "Saving..." : "Save Allocation"}
      </button>
    </div>
  </aside>
{/if}

{#if showBookingDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeBookingDrawer}
    tabindex="-1"
    aria-label="Close booking drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Book Space</h2>
        <p class="mt-1 text-xs text-neutral-500">Create desk or room bookings with approval, check-in, and no-show automation.</p>
      </div>
      <button
        type="button"
        onclick={closeBookingDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close booking drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="space-booking-form" class="space-y-5" onsubmit={handleBookingSubmit}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select bind:value={bookingForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Bookable Space</span>
            <select bind:value={bookingForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select space</option>
              {#each spacesForFacility(bookingForm.facility, { bookableOnly: true }) as space}
                <option value={String(space.facility_space)}>{space.facility_code} • {space.space_label || space.unit_number} • cap {space.capacity}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Booking Title</span>
            <input bind:value={bookingForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Board meeting - Q2 operating review" />
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Purpose</span>
            <textarea bind:value={bookingForm.purpose} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Summarize the booking purpose and expected attendees."></textarea>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Start Time</span>
            <input type="datetime-local" bind:value={bookingForm.start_at} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">End Time</span>
            <input type="datetime-local" bind:value={bookingForm.end_at} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Attendee Count</span>
            <input type="number" min="1" bind:value={bookingForm.attendee_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>
        </section>

        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={bookingForm.notes} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="AV setup required before attendee arrival."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillBooking} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeBookingDrawer} class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">
        Cancel
      </button>
      <button
        type="submit"
        form="space-booking-form"
        disabled={bookingSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {bookingSaving ? "Saving..." : "Save Booking"}
      </button>
    </div>
  </aside>
{/if}
