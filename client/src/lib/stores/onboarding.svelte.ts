import { api, clearTokens } from "$lib/api";
import { ALL_MODULES } from "$lib/modules";

export interface UserMe {
  id: number;
  email: string;
  full_name: string;
  display_name?: string;
  profile_photo_url?: string | null;
  is_superuser: boolean;
  has_completed_tour: boolean;
  has_completed_onboarding: boolean;
  is_demo_account: boolean;
  /** ISO 639-1 language code from UserProfile.default_language. Null if unset. */
  default_language?: string | null;
  organization: {
    id: number;
    name: string;
    industry: string;
    size: string;
    role: string;
    assigned_role: {
      id: number;
      name: string;
      slug: string;
    } | null;
    permissions: string[];
    enabled_modules?: string[];
    addon_modules?: string[];
    is_setup_complete: boolean;
  } | null;
  subscription: {
    status: string;
    edition_key: string;
    edition_name: string;
    trial_end: string | null;
  } | null;
}

interface OnboardingState {
  loaded: boolean;
  showTour: boolean;
  showDemoTour: boolean;
  showCompanySetup: boolean;
  showInviteStaff: boolean;
  showTrialPrompt: boolean;
  showTrialSuccess: boolean;
  showGettingStarted: boolean;
  user: UserMe | null;
}

function shouldShowTrialPrompt(user: UserMe): boolean {
  return (
    !user.is_demo_account &&
    !user.subscription &&
    user.organization?.role === "admin"
  );
}

let state: OnboardingState = $state({
  loaded: false,
  showTour: false,
  showDemoTour: false,
  showCompanySetup: false,
  showInviteStaff: false,
  showTrialPrompt: false,
  showTrialSuccess: false,
  showGettingStarted: false,
  user: null,
});

export const onboarding = {
  get loaded() {
    return state.loaded;
  },
  get showTour() {
    return state.showTour;
  },
  get showDemoTour() {
    return state.showDemoTour;
  },
  get showCompanySetup() {
    return state.showCompanySetup;
  },
  get showInviteStaff() {
    return state.showInviteStaff;
  },
  get showTrialPrompt() {
    return state.showTrialPrompt;
  },
  get showTrialSuccess() {
    return state.showTrialSuccess;
  },
  get showGettingStarted() {
    return state.showGettingStarted;
  },
  get user() {
    return state.user;
  },
  get isOnboarding() {
    return (
      state.showTour ||
      state.showDemoTour ||
      state.showCompanySetup ||
      state.showInviteStaff ||
      state.showTrialPrompt ||
      state.showTrialSuccess ||
      state.showGettingStarted
    );
  },
  get enabledModules(): Set<string> {
    if (state.user?.is_superuser) return ALL_MODULES as Set<string>;
    return new Set(state.user?.organization?.enabled_modules ?? []);
  },
  get addonModules(): Set<string> {
    return new Set(state.user?.organization?.addon_modules ?? []);
  },
  get isTrialing(): boolean {
    return state.user?.subscription?.status === "trialing";
  },
  hasModule(key: string): boolean {
    return this.enabledModules.has(key);
  },

  async load() {
    try {
      const user = await api.get<UserMe>("/auth/me/");
      state.user = user;
      state.loaded = true;

      // Superusers bypass all onboarding
      if (user.is_superuser) return;

      // Demo users get the demo tour instead of standard onboarding
      if (user.is_demo_account && !user.has_completed_tour) {
        state.showDemoTour = true;
        return;
      }

      // Determine which onboarding step to show
      if (!user.has_completed_tour) {
        state.showTour = true;
      } else if (!user.organization || !user.organization.is_setup_complete) {
        // Bootstrap org exists but user hasn't configured it yet
        state.showCompanySetup = true;
      } else if (!user.has_completed_onboarding) {
        // Only admins get the invite staff step; members auto-complete
        if (user.organization.role === "admin") {
          state.showInviteStaff = true;
        } else {
          try {
            await api.post("/auth/complete-onboarding/", {});
            user.has_completed_onboarding = true;
          } catch {
            // Silently fail
          }
        }
      } else if (shouldShowTrialPrompt(user)) {
        // Onboarding complete but no subscription — prompt trial
        state.showTrialPrompt = true;
      } else if (!user.is_demo_account) {
        // Onboarding & subscription done — check if setup tasks remain
        try {
          const gs = await api.get<Record<string, boolean>>("/auth/getting-started-status/");
          const allDone = gs.profile_complete && gs.first_project_created && gs.team_invited;
          if (!allDone) {
            state.showGettingStarted = true;
          }
        } catch {
          // Non-critical — skip getting started on failure
        }
      }
    } catch {
      state.loaded = true;
    }
  },

  async completeTour() {
    try {
      await api.post("/auth/complete-tour/", {});
    } catch {
      // API failure is non-critical — still dismiss the tour
    }
    state.showTour = false;
    if (state.user) {
      state.user.has_completed_tour = true;
    }
    // Show company setup next (if bootstrap org), or invite staff for admins
    if (!state.user?.organization || !state.user.organization.is_setup_complete) {
      state.showCompanySetup = true;
    } else if (!state.user?.has_completed_onboarding) {
      if (state.user.organization.role === "admin") {
        state.showInviteStaff = true;
      } else {
        try {
          await api.post("/auth/complete-onboarding/", {});
          state.user.has_completed_onboarding = true;
        } catch {
          // Silently fail
        }
      }
    }
  },

  async completeDemoTour() {
    try {
      await api.post("/auth/complete-tour/", {});
      await api.post("/auth/complete-onboarding/", {});
      state.showDemoTour = false;
      if (state.user) {
        state.user.has_completed_tour = true;
        state.user.has_completed_onboarding = true;
      }
    } catch {
      state.showDemoTour = false;
    }
  },

  async completeCompanySetup(org: UserMe["organization"]) {
    state.showCompanySetup = false;
    if (state.user) {
      state.user.organization = org;
    }
    // Show invite staff next (only for admins)
    if (org?.role === "admin") {
      state.showInviteStaff = true;
    } else {
      try {
        await api.post("/auth/complete-onboarding/", {});
        if (state.user) state.user.has_completed_onboarding = true;
      } catch {
        // Silently fail
      }
    }
  },

  async completeOnboarding() {
    try {
      await api.post("/auth/complete-onboarding/", {});
      state.showInviteStaff = false;
      if (state.user) {
        state.user.has_completed_onboarding = true;
      }
      // Show trial prompt if no subscription exists (non-demo admins)
      if (state.user && shouldShowTrialPrompt(state.user)) {
        state.showTrialPrompt = true;
      } else {
        // No trial needed — go straight to getting started
        state.showGettingStarted = true;
      }
    } catch {
      state.showInviteStaff = false;
    }
  },

  async startTrial(editionKey: string = "growth") {
    try {
      const res = await api.post<{
        id: number;
        status: string;
        edition_name: string;
        edition_key: string;
        trial_end: string;
      }>("/platform/subscription/start-trial/", { edition_key: editionKey });

      state.showTrialPrompt = false;
      state.showTrialSuccess = true;

      if (state.user) {
        state.user.subscription = {
          status: res.status,
          edition_key: res.edition_key,
          edition_name: res.edition_name,
          trial_end: res.trial_end,
        };
      }

      // Re-fetch user to get updated enabled_modules for the new tier
      try {
        const freshUser = await api.get<UserMe>("/auth/me/");
        if (state.user && freshUser.organization) {
          state.user.organization = freshUser.organization;
        }
      } catch {
        // Non-critical — modules will refresh on next page load
      }
    } catch {
      state.showTrialPrompt = false;
    }
  },

  dismissTrialPrompt() {
    // Log the user out — they'll see the pricing page again on next login
    clearTokens();
    state = {
      loaded: false,
      showTour: false,
      showDemoTour: false,
      showCompanySetup: false,
      showInviteStaff: false,
      showTrialPrompt: false,
      showTrialSuccess: false,
      showGettingStarted: false,
      user: null,
    };
    window.location.href = "/login";
  },

  dismissTrialSuccess() {
    state.showTrialSuccess = false;
    state.showGettingStarted = true;
  },

  dismissGettingStarted() {
    state.showGettingStarted = false;
  },

  replayTour() {
    state.showGettingStarted = false;
    state.showTour = true;
  },

  reset() {
    state = {
      loaded: false,
      showTour: false,
      showDemoTour: false,
      showCompanySetup: false,
      showInviteStaff: false,
      showTrialPrompt: false,
      showTrialSuccess: false,
      showGettingStarted: false,
      user: null,
    };
  },
};
