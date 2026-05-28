import { en, type Messages } from "./messages/en";
import { fr } from "./messages/fr";
import { es } from "./messages/es";
import { ar } from "./messages/ar";

export type LocaleCode = "en" | "fr" | "es" | "ar";

export interface LocaleMeta {
  code: LocaleCode;
  /** Display name in the language itself, e.g. "Français". */
  name: string;
  /** Display name in English, for the language picker tooltip. */
  english: string;
  /** Layout direction for the locale. */
  direction: "ltr" | "rtl";
  /** Compiled message catalogue. */
  messages: Messages;
}

export const LOCALES: Record<LocaleCode, LocaleMeta> = {
  en: { code: "en", name: "English",   english: "English",   direction: "ltr", messages: en },
  fr: { code: "fr", name: "Français",  english: "French",    direction: "ltr", messages: fr },
  es: { code: "es", name: "Español",   english: "Spanish",   direction: "ltr", messages: es },
  ar: { code: "ar", name: "العربية",   english: "Arabic",    direction: "rtl", messages: ar },
};

export const SUPPORTED_LOCALE_CODES: LocaleCode[] = ["en", "fr", "es", "ar"];
export const DEFAULT_LOCALE: LocaleCode = "en";

/** Pick a locale code from a browser language tag, or fall back to en. */
export function detectLocale(): LocaleCode {
  if (typeof navigator === "undefined") return DEFAULT_LOCALE;
  const lang = navigator.language?.toLowerCase() ?? "";
  for (const code of SUPPORTED_LOCALE_CODES) {
    if (lang === code || lang.startsWith(`${code}-`)) return code;
  }
  return DEFAULT_LOCALE;
}
