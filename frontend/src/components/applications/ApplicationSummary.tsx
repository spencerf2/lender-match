import type { ReactNode } from "react";
import type { Application } from "../../api/types";
import { formatDateOnly, formatMoney, formatPercent, humanize, toNumber } from "../../lib/format";
import { Card } from "../ui";

const yesNo = (v: boolean) => (v ? "Yes" : "No");
const orDash = (v: string | number | null | undefined) => (v === null || v === undefined || v === "" ? "—" : String(v));

function Facts({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2 md:grid-cols-3">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="text-gray-500">{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Read-only view of an application in the same sections as the form, plus the backend's derived fields. */
export function ApplicationSummary({ application: app }: { application: Application }) {
  const b = app.business;
  const l = app.loan_request;
  const ratio = toNumber(app.comparable_credit_ratio);
  const downPct = toNumber(app.down_payment_pct);
  return (
    <>
      <Card title="Business">
        <Facts
          items={[
            ["Legal name", orDash(b.legal_name)],
            ["Industry", b.industry ? humanize(b.industry) : "—"],
            ["State", orDash(b.state)],
            ["Founded date", formatDateOnly(b.founded_date)],
            ["Annual revenue", formatMoney(b.annual_revenue)],
            ["Description", orDash(b.description)],
          ]}
        />
      </Card>

      <Card title="Guarantors">
        {app.guarantors.length === 0 ? (
          <p className="text-sm text-gray-600">No guarantors.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b text-gray-600">
              <tr>
                <th className="py-1 pr-3">Name</th>
                <th className="py-1 pr-3">Ownership</th>
                <th className="py-1 pr-3">FICO</th>
                <th className="py-1 pr-3">Homeowner</th>
                <th className="py-1 pr-3">US citizen</th>
                <th className="py-1 pr-3">Bankruptcy discharge</th>
                <th className="py-1 pr-3">Judgments</th>
                <th className="py-1 pr-3">Foreclosures</th>
                <th className="py-1">Repossessions</th>
              </tr>
            </thead>
            <tbody>
              {app.guarantors.map((g, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-1 pr-3">{orDash(g.name)}</td>
                  <td className="py-1 pr-3">{formatPercent(g.ownership_pct, 0)}</td>
                  <td className="py-1 pr-3">{orDash(g.fico)}</td>
                  <td className="py-1 pr-3">{yesNo(g.is_homeowner)}</td>
                  <td className="py-1 pr-3">{yesNo(g.is_us_citizen)}</td>
                  <td className="py-1 pr-3">{formatDateOnly(g.bankruptcy_discharge_date)}</td>
                  <td className="py-1 pr-3">{yesNo(g.has_judgments)}</td>
                  <td className="py-1 pr-3">{yesNo(g.has_foreclosures)}</td>
                  <td className="py-1">{yesNo(g.has_repossessions)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Business credit">
        <Facts items={[["PayNet score", orDash(app.business_credit.paynet_score)]]} />
      </Card>

      <Card title="Trade lines">
        {app.trade_lines.length === 0 ? (
          <p className="text-sm text-gray-600">No trade lines.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b text-gray-600">
              <tr>
                <th className="py-1 pr-3">Creditor</th>
                <th className="py-1 pr-3">Amount</th>
                <th className="py-1 pr-3">Opened on</th>
                <th className="py-1 pr-3">Closed on</th>
                <th className="py-1">Status</th>
              </tr>
            </thead>
            <tbody>
              {app.trade_lines.map((t, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-1 pr-3">{orDash(t.creditor)}</td>
                  <td className="py-1 pr-3">{formatMoney(t.amount)}</td>
                  <td className="py-1 pr-3">{formatDateOnly(t.opened_on)}</td>
                  <td className="py-1 pr-3">{formatDateOnly(t.closed_on)}</td>
                  <td className="py-1">{orDash(t.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Loan request">
        <Facts
          items={[
            ["Amount", formatMoney(l.amount)],
            ["Term", l.term_months === null ? "—" : `${l.term_months} months`],
            ["Down payment", formatMoney(l.down_payment_amount)],
            ["Equipment type", l.equipment_type ? humanize(l.equipment_type) : "—"],
            ["Equipment description", orDash(l.equipment_description)],
            ["Equipment year", orDash(l.equipment_year)],
            ["Equipment mileage", l.equipment_mileage === null ? "—" : l.equipment_mileage.toLocaleString("en-US")],
            ["Private party sale", yesNo(l.is_private_party_sale)],
          ]}
        />
      </Card>

      <Card title="Derived">
        <Facts
          items={[
            ["Minimum FICO", orDash(app.min_fico)],
            ["Has personal guarantor", yesNo(app.has_personal_guarantor)],
            // down_payment_pct is a fraction (0.1 = 10%).
            ["Down payment", downPct === null ? "—" : formatPercent(downPct * 100, 1)],
            ["Comparable credit ratio", ratio === null ? "—" : ratio.toFixed(2)],
          ]}
        />
      </Card>
    </>
  );
}
