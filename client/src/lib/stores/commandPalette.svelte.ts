const STORAGE_KEY = "dos_recent_searches";
const MAX_RECENT = 5;

let isOpen = $state(false);
let recentSearches = $state<string[]>([]);

function loadRecent() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) recentSearches = JSON.parse(raw);
  } catch {
    recentSearches = [];
  }
}

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(recentSearches));
}

export const commandPalette = {
  get isOpen() {
    return isOpen;
  },
  get recentSearches() {
    return recentSearches;
  },

  open() {
    isOpen = true;
  },
  close() {
    isOpen = false;
  },
  toggle() {
    isOpen = !isOpen;
  },

  loadRecent,

  addRecentSearch(q: string) {
    const trimmed = q.trim();
    if (!trimmed) return;
    recentSearches = [trimmed, ...recentSearches.filter((s) => s !== trimmed)].slice(0, MAX_RECENT);
    persist();
  },

  removeRecentSearch(q: string) {
    recentSearches = recentSearches.filter((s) => s !== q);
    persist();
  },

  clearRecentSearches() {
    recentSearches = [];
    persist();
  },
};
