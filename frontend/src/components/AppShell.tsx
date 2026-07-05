import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ReleaseNotes } from "./ReleaseNotes";
import { UserMenu } from "./UserMenu";
import "./app-shell.css";

const links = [
  { to: "/", label: "Trainer", end: true },
  { to: "/dashboard", label: "Dashboard", end: false },
  { to: "/analysis", label: "Analysis", end: false },
  { to: "/coach", label: "AI-Coach", end: false },
  { to: "/settings", label: "Settings", end: false },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [showReleases, setShowReleases] = useState(false);

  return (
    <div className="tf-shell">
      <header className="tf-topbar">
        <div className="tf-brand-group">
          <div className="tf-brand mono">
            Type<span>Forge</span>
          </div>
          <button
            className="tf-version mono"
            onClick={() => setShowReleases(true)}
            title="What's new"
          >
            v{__APP_VERSION__}
          </button>
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
          <UserMenu username={user?.username} />
        </div>
      </header>
      <main className="tf-main">{children}</main>
      <ReleaseNotes open={showReleases} onClose={() => setShowReleases(false)} />
    </div>
  );
}
