import { Link } from "react-router";
import { api } from "../api/client";
import { Card, ErrorBanner, Loading, PageTitle, buttonClass } from "../components/ui";
import { formatDate, formatMoney, humanize } from "../lib/format";
import { useLoad } from "../lib/useLoad";

export function ApplicationsPage() {
  const { data, error, loading } = useLoad(() => api.listApplications(), []);

  return (
    <div>
      <PageTitle
        actions={
          <Link to="/applications/new" className={buttonClass}>
            New application
          </Link>
        }
      >
        Applications
      </PageTitle>
      <ErrorBanner message={error} />
      {loading ? <Loading what="Loading applications" /> : null}
      {data && data.length === 0 ? (
        <p className="text-sm text-gray-600">No applications yet. Create one to match it against lenders.</p>
      ) : null}
      {data && data.length > 0 ? (
        <Card>
          <table className="w-full text-left text-sm">
            <thead className="border-b text-gray-600">
              <tr>
                <th className="py-2 pr-3">Business</th>
                <th className="py-2 pr-3">State</th>
                <th className="py-2 pr-3">Industry</th>
                <th className="py-2 pr-3 text-right">Requested amount</th>
                <th className="py-2 pr-3">Submitted by</th>
                <th className="py-2 pr-3">Created</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {data.map((app) => (
                <tr key={app.id} className="border-b last:border-0">
                  <td className="py-2 pr-3">{app.business.legal_name ?? "Untitled"}</td>
                  <td className="py-2 pr-3">{app.business.state ?? "—"}</td>
                  <td className="py-2 pr-3">{app.business.industry ? humanize(app.business.industry) : "—"}</td>
                  <td className="py-2 pr-3 text-right">{formatMoney(app.loan_request.amount)}</td>
                  <td className="py-2 pr-3">{app.submitted_by ?? "—"}</td>
                  <td className="py-2 pr-3">{formatDate(app.created_at)}</td>
                  <td className="py-2">
                    <Link to={`/applications/${app.id}`} className="text-blue-700 underline">
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </div>
  );
}
