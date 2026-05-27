/**
 * Novestia — Number and currency formatting.
 * Single source of truth. Every price, percent, and quantity routes through here.
 */

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatCurrency(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "$0.00";
  return currencyFormatter.format(num);
}

export function formatCompactCurrency(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "$0";
  return compactFormatter.format(num);
}

export function formatPercent(
  value: string | number,
  options?: { withSign?: boolean },
): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0.00%";
  const withSign = options?.withSign ?? true;
  const sign = withSign && num > 0 ? "+" : "";
  return `${sign}${num.toFixed(2)}%`;
}

export function formatChange(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "$0.00";
  const sign = num > 0 ? "+" : num < 0 ? "-" : "";
  return `${sign}${formatCurrency(Math.abs(num))}`;
}

export function formatQuantity(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0";
  return parseFloat(num.toFixed(8)).toString();
}

export function formatNumber(value: string | number, decimals = 2): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0";
  return num.toFixed(decimals);
}

/** Returns the accent key based on a numeric value's sign */
export function getDeltaColor(value: string | number): "positive" | "negative" | "info" {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (num > 0) return "positive";
  if (num < 0) return "negative";
  return "info";
}
