import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

/**
 * Global single-key navigation: t -> Trainer, d -> Dashboard, s -> Settings,
 * c -> Coach.
 *
 * Only mounted on non-typing pages (Dashboard, Settings, Coach) — never on the
 * Trainer, where those letters are lesson input. Ignores keystrokes typed into
 * form fields so text entry (e.g. the API-key name) isn't hijacked.
 */
export function useNavHotkeys() {
  const navigate = useNavigate();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      const tag = el?.tagName;
      if (
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        el?.isContentEditable
      ) {
        return;
      }
      switch (e.key.toLowerCase()) {
        case "t":
          e.preventDefault();
          navigate("/");
          break;
        case "d":
          e.preventDefault();
          navigate("/dashboard");
          break;
        case "s":
          e.preventDefault();
          navigate("/settings");
          break;
        case "c":
          e.preventDefault();
          navigate("/coach");
          break;
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [navigate]);
}
