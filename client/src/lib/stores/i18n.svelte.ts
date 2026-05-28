import { persistentAtom } from "@nanostores/persistent";
import { api } from "$lib/api";
import {
  LOCALES,
  DEFAULT_LOCALE,
  SUPPORTED_LOCALE_CODES,
  detectLocale,
  type LocaleCode,
} from "$lib/i18n/locales";

/**
 * i18n store — Svelte 5 facade over nanostores.
 *
 * Why both: nanostores' `persistentAtom` gives us free localStorage
 * persistence (and cross-tab sync) for the user's locale choice.
 * Svelte 5 `$state` gives us idiomatic reactivity in templates. The
 * subscribe-to-mirror bridge keeps them in lockstep.
 *
 * `@nanostores/i18n` is installed as a dep for future per-component
 * message scoping (lazy-loaded translations per route). For now, all
 * messages live in a single in-memory catalog per locale — the
 * catalogs are small and tree-shaking handles the unused ones.
 *
 * Precedence on first load:
 *   1. Server preference (UserProfile.default_language via /auth/me/) —
 *      hydrated by `applyServerLocale()` from the layout effect once
 *      onboarding has loaded. Wins over local storage so the locale
 *      syncs across devices.
 *   2. localStorage (if the user has switched languages before)
 *   3. navigator.language (e.g. "fr-FR" → "fr")
 *   4. DEFAULT_LOCALE ("en")
 *
 * On `setLocale()`:
 *   - Update local state + localStorage immediately (instant UI).
 *   - Fire-and-forget PATCH to /auth/profile/ so the choice is
 *     remembered across devices. Failures are silent (the localStorage
 *     copy keeps the experience consistent on this device).
 */

const STORAGE_KEY = "dos-locale";

const localeAtom = persistentAtom<LocaleCode>(STORAGE_KEY, detectLocale(), {
  encode: (value) => value,
  decode: (raw) =>
    (SUPPORTED_LOCALE_CODES as string[]).includes(raw)
      ? (raw as LocaleCode)
      : DEFAULT_LOCALE,
});

let currentLocale = $state<LocaleCode>(localeAtom.get());
localeAtom.subscribe((value) => {
  currentLocale = value;
});

/**
 * Walk a dot-separated key path into the message tree.
 *
 *   resolvePath(en, "common.actions.save") === "Save"
 *
 * Returns `null` if the key isn't present so callers can fall back.
 */
function resolvePath(messages: object, path: string): string | null {
  const segments = path.split(".");
  let cursor: unknown = messages;
  for (const seg of segments) {
    if (cursor && typeof cursor === "object" && seg in cursor) {
      cursor = (cursor as Record<string, unknown>)[seg];
    } else {
      return null;
    }
  }
  return typeof cursor === "string" ? cursor : null;
}

/**
 * Replace `{name}` placeholders with values from `params`.
 * Missing params leave the placeholder visible so it's easy to spot.
 */
function interpolate(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) =>
    key in params ? String(params[key]) : `{${key}}`,
  );
}

export const i18n = {
  /** Current locale code (reactive in Svelte components). */
  get locale() {
    return currentLocale;
  },
  /** Layout direction for the current locale. Bind to <html dir="...">. */
  get direction() {
    return LOCALES[currentLocale].direction;
  },
  /** All supported locales — used by the language picker. */
  get available() {
    return SUPPORTED_LOCALE_CODES.map((code) => LOCALES[code]);
  },

  /**
   * Apply a locale value sourced from the server (e.g. UserMe payload).
   * Skipped when the value is missing, unsupported, or already active.
   * Does NOT trigger a PATCH back — this is the inbound side only.
   */
  applyServerLocale(code: string | null | undefined) {
    if (!code) return;
    const normalized = code.toLowerCase();
    if (!(SUPPORTED_LOCALE_CODES as string[]).includes(normalized)) return;
    if (currentLocale === normalized) return;
    localeAtom.set(normalized as LocaleCode);
  },

  setLocale(code: LocaleCode) {
    if (!(code in LOCALES)) return;
    if (currentLocale === code) return;
    localeAtom.set(code);
    // Fire-and-forget — the locale is already applied locally; the
    // server roundtrip just persists it for other devices/sessions.
    void api.patch("/auth/profile/", { default_language: code }).catch((err) => {
      console.error("[i18n] failed to persist locale to server:", err);
    });
  },

  /**
   * Translate a key path into the current locale's string. Falls back
   * to the English catalog, then to the raw key. Optional `params`
   * substitute `{name}` placeholders.
   */
  t(path: string, params?: Record<string, string | number>): string {
    const messages = LOCALES[currentLocale].messages;
    let value = resolvePath(messages, path);
    if (value === null) value = resolvePath(LOCALES[DEFAULT_LOCALE].messages, path);
    if (value === null) return path;
    return params ? interpolate(value, params) : value;
  },
};
