import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Money arrives from the API as a decimal string and stays a string here.
 * Parsing it to a JS number would reintroduce float error into figures the backend
 * went to considerable trouble to keep exact (AP-2).
 */
export function formatMoney(value: string, currency = "GBP"): string {
  const [whole, fraction = ""] = value.split(".");
  const withSeparators = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const decimals = fraction.slice(0, 2).padEnd(2, "0");
  const symbol = currency === "GBP" ? "£" : "";
  return `${symbol}${withSeparators}.${decimals}`;
}

export function shortHash(hash: string | null | undefined, length = 10): string {
  if (!hash) return "—";
  return `${hash.slice(0, length)}…`;
}
