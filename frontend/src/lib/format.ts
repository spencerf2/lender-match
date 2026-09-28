import type { Decimal, FieldDefinition } from "../api/types";

export function toNumber(value: Decimal | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function formatMoney(value: Decimal | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function formatPercent(value: Decimal | null | undefined, digits = 2): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return `${n.toFixed(digits)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

export function formatDateOnly(value: string | null | undefined): string {
  if (!value) return "—";
  return value;
}

/** "class_8_truck" -> "class 8 truck" */
export function humanize(value: string): string {
  return value.replace(/_/g, " ");
}

export function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

/** The field's label from GET /application-fields, first letter capitalized, or the key when unknown. */
export function fieldLabel(fields: FieldDefinition[] | null, key: string): string {
  const label = fields?.find((f) => f.key === key)?.label;
  return label ? capitalize(label) : key;
}
