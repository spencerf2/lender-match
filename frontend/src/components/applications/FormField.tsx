import type { ReactNode } from "react";
import { labelClass } from "../ui";

export function FormField({
  label,
  error,
  required,
  children,
  className = "",
}: {
  label: string;
  error?: string | undefined;
  required?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`block ${className}`}>
      <span className={labelClass}>
        {label}
        {required ? <span className="text-red-700"> *</span> : null}
      </span>
      <span className="mt-1 block">{children}</span>
      {error ? <span className="mt-1 block text-xs text-red-700">{error}</span> : null}
    </label>
  );
}

export function Checkbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-gray-700">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}
