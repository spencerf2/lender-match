import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../api/client";
import { Checkbox, FormField } from "../components/applications/FormField";
import {
  emptyForm,
  emptyGuarantor,
  emptyTradeLine,
  toDraft,
} from "../components/applications/formState";
import type { ApplicationForm } from "../components/applications/formState";
import { mapServerErrors, validateDraft } from "../components/applications/validate";
import {
  Card,
  ErrorBanner,
  Loading,
  PageTitle,
  buttonClass,
  inputClass,
  secondaryButtonClass,
} from "../components/ui";
import { humanize } from "../lib/format";
import { errorMessage, useLoad } from "../lib/useLoad";

export function NewApplicationPage() {
  const navigate = useNavigate();
  const fields = useLoad(() => api.applicationFields(), []);
  const [form, setForm] = useState<ApplicationForm>(emptyForm);
  const [attempted, setAttempted] = useState(false);
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [bannerErrors, setBannerErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const clientErrors = useMemo(() => validateDraft(toDraft(form)), [form]);
  const shown: Record<string, string> = attempted ? { ...clientErrors, ...serverErrors } : serverErrors;
  const clientErrorCount = Object.keys(clientErrors).length;

  const update = (mutate: (draft: ApplicationForm) => void) => {
    setForm((prev) => {
      const next = structuredClone(prev);
      mutate(next);
      return next;
    });
    setServerErrors({});
    setBannerErrors([]);
  };

  const options = (key: string): string[] => fields.data?.find((f) => f.key === key)?.values ?? [];

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    if (clientErrorCount > 0) return;
    setSubmitting(true);
    setBannerErrors([]);
    try {
      const created = await api.createApplication(toDraft(form));
      navigate(`/applications/${created.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.validationErrors) {
        const { fields: mapped, unmapped } = mapServerErrors(err.validationErrors);
        setServerErrors(mapped);
        setBannerErrors(unmapped.length > 0 || Object.keys(mapped).length === 0 ? [err.message, ...unmapped] : []);
      } else {
        setBannerErrors([errorMessage(err)]);
      }
      setSubmitting(false);
    }
  }

  if (fields.loading) return <Loading what="Loading application fields" />;
  if (fields.error || !fields.data)
    return <ErrorBanner message={`Could not load application fields: ${fields.error ?? "no data"}`} />;

  const select = (key: string, value: string, onChange: (v: string) => void, humanizeValues = false) => (
    <select className={inputClass} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Select…</option>
      {options(key).map((v) => (
        <option key={v} value={v}>
          {humanizeValues ? humanize(v) : v}
        </option>
      ))}
    </select>
  );

  const b = form.business;
  const l = form.loan_request;
  const displayedCount = Object.keys(shown).length;

  return (
    <form onSubmit={onSubmit} noValidate>
      <PageTitle>New application</PageTitle>

      <Card>
        <FormField label="Submitted by" error={shown["submitted_by"]} className="max-w-sm">
          <input
            className={inputClass}
            value={form.submitted_by}
            onChange={(e) => update((f) => void (f.submitted_by = e.target.value))}
          />
        </FormField>
      </Card>

      <Card title="Business">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <FormField label="Legal name" error={shown["business.legal_name"]}>
            <input
              className={inputClass}
              value={b.legal_name}
              onChange={(e) => update((f) => void (f.business.legal_name = e.target.value))}
            />
          </FormField>
          <FormField label="Industry" required error={shown["business.industry"]}>
            {select("business.industry", b.industry, (v) => update((f) => void (f.business.industry = v)), true)}
          </FormField>
          <FormField label="State" required error={shown["business.state"]}>
            {select("business.state", b.state, (v) => update((f) => void (f.business.state = v)))}
          </FormField>
          <FormField label="Founded date" error={shown["business.founded_date"]}>
            <input
              type="date"
              className={inputClass}
              value={b.founded_date}
              onChange={(e) => update((f) => void (f.business.founded_date = e.target.value))}
            />
          </FormField>
          <FormField label="Annual revenue ($)" error={shown["business.annual_revenue"]}>
            <input
              type="number"
              min={0}
              className={inputClass}
              value={b.annual_revenue}
              onChange={(e) => update((f) => void (f.business.annual_revenue = e.target.value))}
            />
          </FormField>
        </div>
        <FormField label="Description" error={shown["business.description"]} className="mt-3">
          <textarea
            rows={2}
            className={inputClass}
            value={b.description}
            onChange={(e) => update((f) => void (f.business.description = e.target.value))}
          />
        </FormField>
      </Card>

      <Card title="Guarantors">
        <ErrorBanner message={shown["guarantors"] ?? null} />
        {form.guarantors.map((g, i) => {
          const key = (name: string) => shown[`guarantors.${i}.${name}`];
          const set = (mutate: (row: ApplicationForm["guarantors"][number]) => void) =>
            update((f) => {
              const row = f.guarantors[i];
              if (row) mutate(row);
            });
          return (
            <div key={i} className="mb-3 rounded border border-gray-200 p-3">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-medium">Guarantor {i + 1}</h3>
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={() => update((f) => void f.guarantors.splice(i, 1))}
                >
                  Remove
                </button>
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
                <FormField label="Name" error={key("name")}>
                  <input className={inputClass} value={g.name} onChange={(e) => set((r) => void (r.name = e.target.value))} />
                </FormField>
                <FormField label="Ownership (%)" error={key("ownership_pct")}>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    className={inputClass}
                    value={g.ownership_pct}
                    onChange={(e) => set((r) => void (r.ownership_pct = e.target.value))}
                  />
                </FormField>
                <FormField label="FICO" required={i === 0} error={key("fico")}>
                  <input
                    type="number"
                    min={300}
                    max={850}
                    className={inputClass}
                    value={g.fico}
                    onChange={(e) => set((r) => void (r.fico = e.target.value))}
                  />
                </FormField>
                <FormField label="Bankruptcy discharge date" error={key("bankruptcy_discharge_date")}>
                  <input
                    type="date"
                    className={inputClass}
                    value={g.bankruptcy_discharge_date}
                    onChange={(e) => set((r) => void (r.bankruptcy_discharge_date = e.target.value))}
                  />
                </FormField>
              </div>
              <div className="mt-3 flex flex-wrap gap-4">
                <Checkbox label="Homeowner" checked={g.is_homeowner} onChange={(c) => set((r) => void (r.is_homeowner = c))} />
                <Checkbox label="US citizen" checked={g.is_us_citizen} onChange={(c) => set((r) => void (r.is_us_citizen = c))} />
                <Checkbox label="Has judgments" checked={g.has_judgments} onChange={(c) => set((r) => void (r.has_judgments = c))} />
                <Checkbox
                  label="Has foreclosures"
                  checked={g.has_foreclosures}
                  onChange={(c) => set((r) => void (r.has_foreclosures = c))}
                />
                <Checkbox
                  label="Has repossessions"
                  checked={g.has_repossessions}
                  onChange={(c) => set((r) => void (r.has_repossessions = c))}
                />
              </div>
            </div>
          );
        })}
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={() => update((f) => void f.guarantors.push(emptyGuarantor()))}
        >
          Add guarantor
        </button>
      </Card>

      <Card title="Business credit">
        <FormField label="PayNet score" error={shown["business_credit.paynet_score"]} className="max-w-xs">
          <input
            type="number"
            min={0}
            max={1000}
            className={inputClass}
            value={form.business_credit.paynet_score}
            onChange={(e) => update((f) => void (f.business_credit.paynet_score = e.target.value))}
          />
        </FormField>
      </Card>

      <Card title="Trade lines">
        {form.trade_lines.length === 0 ? <p className="mb-3 text-sm text-gray-600">No trade lines.</p> : null}
        {form.trade_lines.map((t, i) => {
          const key = (name: string) => shown[`trade_lines.${i}.${name}`];
          const set = (mutate: (row: ApplicationForm["trade_lines"][number]) => void) =>
            update((f) => {
              const row = f.trade_lines[i];
              if (row) mutate(row);
            });
          return (
            <div key={i} className="mb-3 grid grid-cols-1 items-end gap-3 rounded border border-gray-200 p-3 md:grid-cols-6">
              <FormField label="Creditor" error={key("creditor")}>
                <input className={inputClass} value={t.creditor} onChange={(e) => set((r) => void (r.creditor = e.target.value))} />
              </FormField>
              <FormField label="Amount ($)" error={key("amount")}>
                <input
                  type="number"
                  min={0}
                  className={inputClass}
                  value={t.amount}
                  onChange={(e) => set((r) => void (r.amount = e.target.value))}
                />
              </FormField>
              <FormField label="Opened on" error={key("opened_on")}>
                <input
                  type="date"
                  className={inputClass}
                  value={t.opened_on}
                  onChange={(e) => set((r) => void (r.opened_on = e.target.value))}
                />
              </FormField>
              <FormField label="Closed on" error={key("closed_on")}>
                <input
                  type="date"
                  className={inputClass}
                  value={t.closed_on}
                  onChange={(e) => set((r) => void (r.closed_on = e.target.value))}
                />
              </FormField>
              <FormField label="Status" error={key("status")}>
                <input className={inputClass} value={t.status} onChange={(e) => set((r) => void (r.status = e.target.value))} />
              </FormField>
              <div>
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={() => update((f) => void f.trade_lines.splice(i, 1))}
                >
                  Remove
                </button>
              </div>
            </div>
          );
        })}
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={() => update((f) => void f.trade_lines.push(emptyTradeLine()))}
        >
          Add trade line
        </button>
      </Card>

      <Card title="Loan request">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <FormField label="Amount ($)" required error={shown["loan_request.amount"]}>
            <input
              type="number"
              min={0}
              className={inputClass}
              value={l.amount}
              onChange={(e) => update((f) => void (f.loan_request.amount = e.target.value))}
            />
          </FormField>
          <FormField label="Term (months)" required error={shown["loan_request.term_months"]}>
            <input
              type="number"
              min={1}
              step={1}
              className={inputClass}
              value={l.term_months}
              onChange={(e) => update((f) => void (f.loan_request.term_months = e.target.value))}
            />
          </FormField>
          <FormField label="Down payment ($)" error={shown["loan_request.down_payment_amount"]}>
            <input
              type="number"
              min={0}
              className={inputClass}
              value={l.down_payment_amount}
              onChange={(e) => update((f) => void (f.loan_request.down_payment_amount = e.target.value))}
            />
          </FormField>
          <FormField label="Equipment type" required error={shown["loan_request.equipment_type"]}>
            {select("equipment.type", l.equipment_type, (v) => update((f) => void (f.loan_request.equipment_type = v)), true)}
          </FormField>
          <FormField label="Equipment year" error={shown["loan_request.equipment_year"]}>
            <input
              type="number"
              min={1900}
              className={inputClass}
              value={l.equipment_year}
              onChange={(e) => update((f) => void (f.loan_request.equipment_year = e.target.value))}
            />
          </FormField>
          <FormField label="Equipment mileage" error={shown["loan_request.equipment_mileage"]}>
            <input
              type="number"
              min={0}
              className={inputClass}
              value={l.equipment_mileage}
              onChange={(e) => update((f) => void (f.loan_request.equipment_mileage = e.target.value))}
            />
          </FormField>
        </div>
        <FormField label="Equipment description" error={shown["loan_request.equipment_description"]} className="mt-3">
          <input
            className={inputClass}
            value={l.equipment_description}
            onChange={(e) => update((f) => void (f.loan_request.equipment_description = e.target.value))}
          />
        </FormField>
        <div className="mt-3">
          <Checkbox
            label="Private party sale"
            checked={l.is_private_party_sale}
            onChange={(c) => update((f) => void (f.loan_request.is_private_party_sale = c))}
          />
        </div>
      </Card>

      <div className="space-y-2">
        {bannerErrors.map((message) => (
          <ErrorBanner key={message} message={message} />
        ))}
        {displayedCount > 0 ? (
          <p className="text-sm text-red-700">
            {displayedCount === 1 ? "1 field needs attention." : `${displayedCount} fields need attention.`}
          </p>
        ) : null}
        <button type="submit" className={buttonClass} disabled={submitting || (attempted && clientErrorCount > 0)}>
          {submitting ? "Creating…" : "Create application"}
        </button>
      </div>
    </form>
  );
}
