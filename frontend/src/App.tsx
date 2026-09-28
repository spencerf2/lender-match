import { NavLink, Navigate, Route, Routes } from "react-router";
import { ApplicationsPage } from "./pages/ApplicationsPage";
import { NewApplicationPage } from "./pages/NewApplicationPage";
import { ApplicationDetailPage } from "./pages/ApplicationDetailPage";
import { LendersPage } from "./pages/LendersPage";
import { LenderDetailPage } from "./pages/LenderDetailPage";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded text-sm font-medium ${
    isActive ? "bg-gray-900 text-white" : "text-gray-700 hover:bg-gray-200"
  }`;

export function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b bg-white">
        <nav className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
          <span className="mr-4 text-lg font-semibold">Lender Match</span>
          <NavLink to="/applications" className={navClass}>
            Applications
          </NavLink>
          <NavLink to="/lenders" className={navClass}>
            Lenders
          </NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/applications" replace />} />
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/applications/new" element={<NewApplicationPage />} />
          <Route path="/applications/:id" element={<ApplicationDetailPage />} />
          <Route path="/lenders" element={<LendersPage />} />
          <Route path="/lenders/:id" element={<LenderDetailPage />} />
          <Route path="*" element={<p className="text-gray-600">Page not found.</p>} />
        </Routes>
      </main>
    </div>
  );
}
