/**
 * Locale → currency detection.
 *
 * The user's browser exposes their locale via `navigator.language` (e.g.
 * "en-NG", "fr-FR", "es-MX"). From the locale we can derive a region code,
 * and from the region code we can derive a default currency.
 *
 * Used by the currency store as a fallback when the org has no explicit
 * preference (i.e. when `default_currency` comes back as the "XXX"
 * placeholder from the backend).
 *
 * The map below covers the ~60 countries with the most active accounts and
 * the Eurozone. Anything not on the list falls back to USD. Adding a new
 * country is one line; the runtime cost is a single object lookup.
 */

const COUNTRY_TO_CURRENCY: Record<string, string> = {
  // Africa
  NG: "NGN", // Nigeria
  ZA: "ZAR", // South Africa
  KE: "KES", // Kenya
  GH: "GHS", // Ghana
  EG: "EGP", // Egypt
  MA: "MAD", // Morocco
  ET: "ETB", // Ethiopia
  TZ: "TZS", // Tanzania
  UG: "UGX", // Uganda
  RW: "RWF", // Rwanda
  CI: "XOF", // Côte d'Ivoire (West African CFA)
  SN: "XOF", // Senegal

  // Americas
  US: "USD",
  CA: "CAD",
  MX: "MXN",
  BR: "BRL",
  AR: "ARS",
  CL: "CLP",
  CO: "COP",
  PE: "PEN",

  // Europe (Eurozone members default to EUR)
  AT: "EUR", BE: "EUR", CY: "EUR", DE: "EUR", EE: "EUR",
  ES: "EUR", FI: "EUR", FR: "EUR", GR: "EUR", HR: "EUR",
  IE: "EUR", IT: "EUR", LT: "EUR", LU: "EUR", LV: "EUR",
  MT: "EUR", NL: "EUR", PT: "EUR", SI: "EUR", SK: "EUR",

  // Europe (non-Euro)
  GB: "GBP",
  CH: "CHF",
  SE: "SEK",
  NO: "NOK",
  DK: "DKK",
  PL: "PLN",
  CZ: "CZK",
  HU: "HUF",
  RO: "RON",
  BG: "BGN",
  RU: "RUB",
  UA: "UAH",
  TR: "TRY",

  // Middle East
  AE: "AED", // UAE
  SA: "SAR", // Saudi Arabia
  IL: "ILS",
  QA: "QAR",
  KW: "KWD",
  BH: "BHD",
  OM: "OMR",

  // Asia / Pacific
  IN: "INR",
  CN: "CNY",
  JP: "JPY",
  KR: "KRW",
  SG: "SGD",
  HK: "HKD",
  TW: "TWD",
  MY: "MYR",
  TH: "THB",
  ID: "IDR",
  PH: "PHP",
  VN: "VND",
  AU: "AUD",
  NZ: "NZD",
  PK: "PKR",
  BD: "BDT",
  LK: "LKR",
};

/**
 * Resolve the user's most likely currency from `navigator.language`.
 *
 * Returns `null` if the browser doesn't expose enough info to make a
 * confident guess — the caller should fall back to the configured default
 * (typically USD or the org-level setting).
 */
export function detectCurrencyFromLocale(): string | null {
  if (typeof navigator === "undefined") return null;
  const lang = navigator.language;
  if (!lang) return null;

  try {
    const locale = new Intl.Locale(lang);
    // .maximize() fills in the region (e.g. "en" → "en-Latn-US") so we get
    // a country code even when the user only set a language.
    const region = locale.maximize().region;
    if (!region) return null;
    return COUNTRY_TO_CURRENCY[region] ?? null;
  } catch {
    return null;
  }
}

export const KNOWN_COUNTRIES = Object.keys(COUNTRY_TO_CURRENCY);
