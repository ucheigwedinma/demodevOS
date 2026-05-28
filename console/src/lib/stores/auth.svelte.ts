import { api } from "$lib/api";

export interface ConsoleUser {
  id: number;
  email: string;
  full_name: string;
  display_name?: string;
  profile_photo_url?: string | null;
  is_superuser: boolean;
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
  } | null;
  subscription: {
    status: string;
    edition_key: string;
    edition_name: string;
    trial_end: string | null;
  } | null;
}

let user = $state<ConsoleUser | null>(null);
let loaded = $state(false);

export const auth = {
  get user() {
    return user;
  },
  get loaded() {
    return loaded;
  },
  get isAuthenticated() {
    return !!user;
  },
  get isSuperuser() {
    return user?.is_superuser ?? false;
  },

  async load() {
    try {
      user = await api.get<ConsoleUser>("/auth/me/");
      loaded = true;
    } catch {
      user = null;
      loaded = true;
    }
  },

  reset() {
    user = null;
    loaded = false;
  },

  logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
    user = null;
    loaded = false;
    window.location.href = "/login";
  },
};
