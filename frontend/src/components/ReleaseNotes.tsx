import { useEffect } from "react";
import { RELEASES, type ReleaseSection } from "../releaseNotes";
import "./release-notes.css";

const SECTION_META: {
  key: keyof ReleaseSection;
  label: string;
  cls: string;
}[] = [
  { key: "added", label: "New", cls: "tf-rn-badge--added" },
  { key: "changed", label: "Changed", cls: "tf-rn-badge--changed" },
  { key: "fixed", label: "Fixed", cls: "tf-rn-badge--fixed" },
];

export function ReleaseNotes({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="tf-rn-overlay" onClick={onClose}>
      <div
        className="tf-rn"
        role="dialog"
        aria-label="Release notes"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="tf-rn-head">
          <h2>Release Notes</h2>
          <span className="tf-rn-current mono">current v{__APP_VERSION__}</span>
          <button className="tf-rn-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="tf-rn-body">
          {RELEASES.map((rel) => {
            const isCurrent = rel.version === __APP_VERSION__;
            return (
              <section key={rel.version} className="tf-rn-release">
                <div className="tf-rn-version">
                  <span className="mono tf-rn-vnum">v{rel.version}</span>
                  {isCurrent && <span className="tf-rn-tag">Current</span>}
                  <span className="tf-rn-date">{rel.date}</span>
                </div>
                {SECTION_META.map(({ key, label, cls }) => {
                  const items = rel.sections[key];
                  if (!items || items.length === 0) return null;
                  return (
                    <div key={key} className="tf-rn-section">
                      <span className={`tf-rn-badge ${cls}`}>{label}</span>
                      <ul className="tf-rn-list">
                        {items.map((it, i) => (
                          <li key={i}>{it}</li>
                        ))}
                      </ul>
                    </div>
                  );
                })}
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}
