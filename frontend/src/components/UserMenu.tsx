import { useEffect, useRef, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { authApi } from "../api/endpoints";
import { useClearAuth } from "../hooks/useAuth";

// Top-right account dropdown: Profile, Settings, Log out.
export function UserMenu({ username }: { username?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const clearAuth = useClearAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function handleLogout() {
    setOpen(false);
    try {
      await authApi.logout();
    } finally {
      clearAuth();
      navigate("/login", { replace: true });
    }
  }

  const itemClass = ({ isActive }: { isActive: boolean }) =>
    `tf-usermenu-item${isActive ? " tf-usermenu-item--active" : ""}`;

  return (
    <div className="tf-usermenu" ref={ref}>
      <button
        className="tf-usermenu-trigger mono"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        {username ?? "account"}
        <span className="tf-usermenu-caret" aria-hidden>▾</span>
      </button>

      {open && (
        <div className="tf-usermenu-dropdown" role="menu">
          <NavLink to="/profile" className={itemClass} role="menuitem" onClick={() => setOpen(false)}>
            Profile
          </NavLink>
          <NavLink to="/settings" className={itemClass} role="menuitem" onClick={() => setOpen(false)}>
            Settings
          </NavLink>
          <div className="tf-usermenu-sep" />
          <button
            className="tf-usermenu-item tf-usermenu-item--danger"
            role="menuitem"
            onClick={handleLogout}
          >
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
