import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { authApi } from "../api/endpoints";
import { useAuth, useInvalidateAuth } from "../hooks/useAuth";
import "./app-shell.css";

const links = [
  { to: "/", label: "Trainer", end: true },
  { to: "/dashboard", label: "Dashboard", end: false },
  { to: "/settings", label: "Settings", end: false },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const invalidate = useInvalidateAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      await authApi.logout();
    } finally {
      invalidate();
      navigate("/login", { replace: true });
    }
  }

  return (
    <div className="tf-shell">
      <header className="tf-topbar">
        <div className="tf-brand mono">
          Type<span>Forge</span>
        </div>
        <nav className="tf-nav">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `tf-navlink${isActive ? " tf-navlink--active" : ""}`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="tf-topbar-right">
          <span className="tf-user mono">{user?.username}</span>
          <button className="tf-logout" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </header>
      <main className="tf-main">{children}</main>
    </div>
  );
}
