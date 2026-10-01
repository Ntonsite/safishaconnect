import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { Role } from "../api/types";
import { FullPageSpinner } from "../shared/components/Feedback";
import { homeFor, useAuth } from "./AuthContext";

/** Client-side guard for UX only — every endpoint enforces RBAC on the server. */
export function RequireRole({ role }: { role: Role }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <FullPageSpinner />;
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (user.role !== role) return <Navigate to={homeFor(user.role)} replace />;
  return <Outlet />;
}
