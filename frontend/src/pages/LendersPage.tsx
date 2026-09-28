import { useState } from "react";
import { Link } from "react-router";
import { api } from "../api/client";
import { useLoad } from "../lib/useLoad";
import { buttonClass, Card, ErrorBanner, Loading, PageTitle } from "../components/ui";
import { NewLenderForm } from "../components/lenders/NewLenderForm";

export function LendersPage() {
  const { data: lenders, error, loading } = useLoad(() => api.listLenders(), []);
  const [adding, setAdding] = useState(false);

  return (
    <div>
      <PageTitle
        actions={
          adding ? null : (
            <button type="button" className={buttonClass} onClick={() => setAdding(true)}>
              Add lender
            </button>
          )
        }
      >
        Lenders
      </PageTitle>
      {adding ? <NewLenderForm onClose={() => setAdding(false)} /> : null}
      <ErrorBanner message={error} />
      {loading ? <Loading what="Loading lenders" /> : null}
      {!loading && !error && lenders?.length === 0 ? (
        <p className="text-sm text-gray-600">No lenders yet.</p>
      ) : null}
      {lenders && lenders.length > 0 ? (
        <Card>
          <table className="w-full text-left text-sm">
            <thead className="border-b text-gray-600">
              <tr>
                <th className="py-2 pr-4 font-medium">Name</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium">Programs</th>
                <th className="py-2 pr-4 font-medium">Source effective date</th>
                <th className="py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {lenders.map((lender) => (
                <tr key={lender.id} className="border-b last:border-0">
                  <td className="py-2 pr-4">{lender.name}</td>
                  <td className="py-2 pr-4">{lender.status}</td>
                  <td className="py-2 pr-4">{lender.programs.length}</td>
                  <td className="py-2 pr-4">{lender.source_effective_date ?? "—"}</td>
                  <td className="py-2">
                    <Link to={`/lenders/${lender.id}`} className="text-blue-700 underline">
                      View policy
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
