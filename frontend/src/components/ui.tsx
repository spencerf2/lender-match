import type { ReactNode } from "react";

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div role="alert" className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
      {message}
    </div>
  );
}

export function Loading({ what = "Loading" }: { what?: string }) {
  return (
    <p role="status" className="text-sm text-gray-500">
      {what}…
    </p>
  );
}

export function PageTitle({ children, actions }: { children: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h1 className="text-2xl font-semibold">{children}</h1>
      {actions}
    </div>
  );
}

export function Card({ title, children }: { title?: ReactNode; children: ReactNode }) {
  return (
    <section className="mb-4 rounded border bg-white p-4">
      {title ? <h2 className="mb-3 text-lg font-medium">{title}</h2> : null}
      {children}
    </section>
  );
}

export const buttonClass =
  "inline-flex items-center rounded bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50";
export const secondaryButtonClass =
  "inline-flex items-center rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-800 hover:bg-gray-100 disabled:opacity-50";
export const inputClass =
  "w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none";
export const labelClass = "block text-sm font-medium text-gray-700";
