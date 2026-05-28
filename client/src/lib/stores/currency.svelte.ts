import { api } from "$lib/api";
import { detectCurrencyFromLocale } from "$lib/locale-currency";

export interface CurrencyConfig {
  code: string;
  symbol: string;
  position: "prefix" | "suffix";
  decimals: number;
}

/**
 * ISO 4217 placeholder code returned by the backend when the org has not
 * explicitly chosen a currency. Treated as "no preference" — the store
 * falls back to detecting the user's currency from `navigator.language`.
 */
const PLACEHOLDER_CURRENCY_CODE = "XXX";
const FALLBACK_CURRENCY_CODE = "USD";

function resolveCurrencySymbol(code: string): string {
  try {
    const parts = new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      currencyDisplay: "narrowSymbol",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).formatToParts(0);
    return parts.find((part) => part.type === "currency")?.value ?? code;
  } catch {
    return code;
  }
}

function normalizeNumber(value: string | number): number | null {
  const parsed = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Compose a formatted amount with its currency symbol.
 *
 * - Single-character symbols ($, €, ₦, ₹, ¥) sit flush against the digits.
 * - Multi-character symbols (CHF, NOK, SEK, the XXX fallback, etc.) get a
 *   non-breaking space — "CHF 1,234.56" reads correctly; "CHF1,234.56"
 *   does not.
 * - For prefixed currencies, a negative sign is hoisted outside the symbol
 *   so amounts read "-$100.00" rather than "$-100.00". Suffix currencies
 *   keep the natural "100.00- kr" ordering (rare in practice).
 */
function applyCurrencySymbol(symbol: string, position: "prefix" | "suffix", formatted: string): string {
  const gap = symbol.length > 1 ? " " : "";
  if (position === "suffix") {
    return `${formatted}${gap}${symbol}`;
  }
  if (formatted.startsWith("-")) {
    return `-${symbol}${gap}${formatted.slice(1)}`;
  }
  return `${symbol}${gap}${formatted}`;
}

let config: CurrencyConfig = $state({
  code: FALLBACK_CURRENCY_CODE,
  symbol: resolveCurrencySymbol(FALLBACK_CURRENCY_CODE),
  position: "prefix",
  decimals: 2,
});

let loaded = $state(false);
/**
 * True when the active config came from the user's browser locale rather
 * than from an org preference. The settings page can show a "Detected
 * from your location" hint and a CTA to make it explicit.
 */
let isLocationDetected = $state(false);

export const currency = {
  get config() {
    return config;
  },
  get loaded() {
    return loaded;
  },
  get isLocationDetected() {
    return isLocationDetected;
  },

  /**
   * Precedence rule:
   *   1. If the org pref is anything other than the XXX placeholder, use it.
   *   2. Otherwise, detect from `navigator.language` (e.g. "en-NG" → NGN).
   *   3. If detection fails (unknown region), fall back to USD.
   *
   * In short: location is the default for first-time users, and the org
   * pref overrides only after someone has explicitly set one.
   */
  async load() {
    try {
      const data = await api.get<{
        default_currency: string;
        currency_position: "prefix" | "suffix";
        currency_decimal_places: number;
      }>("/settings/preferences/");

      const explicit = data.default_currency && data.default_currency !== PLACEHOLDER_CURRENCY_CODE;
      const code = explicit
        ? data.default_currency
        : detectCurrencyFromLocale() ?? FALLBACK_CURRENCY_CODE;

      config = {
        code,
        symbol: resolveCurrencySymbol(code),
        position: data.currency_position,
        decimals: data.currency_decimal_places,
      };
      isLocationDetected = !explicit;
    } catch {
      // Even if the prefs endpoint fails, give the user a sensible default
      // based on their locale rather than the XXX placeholder.
      const code = detectCurrencyFromLocale() ?? FALLBACK_CURRENCY_CODE;
      config = {
        code,
        symbol: resolveCurrencySymbol(code),
        position: "prefix",
        decimals: 2,
      };
      isLocationDetected = true;
    } finally {
      loaded = true;
    }
  },

  update(partial: Partial<CurrencyConfig>) {
    config = { ...config, ...partial };
    // An explicit update is by definition no longer location-driven.
    if (partial.code) isLocationDetected = false;
  },

  format(value: string | number): string {
    const n = normalizeNumber(value);
    if (n === null) return String(value);
    const formatted = n.toLocaleString(undefined, {
      minimumFractionDigits: config.decimals,
      maximumFractionDigits: config.decimals,
    });
    return applyCurrencySymbol(config.symbol, config.position, formatted);
  },

  /** Format with no decimals (for summary KPIs) */
  formatCompact(value: string | number): string {
    const n = normalizeNumber(value);
    if (n === null) return String(value);
    const formatted = n.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    });
    return applyCurrencySymbol(config.symbol, config.position, formatted);
  },

  /** Format in abbreviated form (K/M/B) for dense charts and KPI rows. */
  formatAbbreviated(value: string | number): string {
    const n = normalizeNumber(value);
    if (n === null) return String(value);
    const abs = Math.abs(n);
    let compactValue: string;
    if (abs >= 1_000_000_000) {
      compactValue = `${(n / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
    } else if (abs >= 1_000_000) {
      compactValue = `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
    } else if (abs >= 1_000) {
      // Match M/B precision so charts don't render "1K" next to "1.2M".
      compactValue = `${(n / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
    } else {
      compactValue = n.toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      });
    }
    return applyCurrencySymbol(config.symbol, config.position, compactValue);
  },

  reset() {
    config = {
      code: FALLBACK_CURRENCY_CODE,
      symbol: resolveCurrencySymbol(FALLBACK_CURRENCY_CODE),
      position: "prefix",
      decimals: 2,
    };
    loaded = false;
    isLocationDetected = false;
  },
};
