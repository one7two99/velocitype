import { useNavigate } from "react-router-dom";
import type { WeakKeyInfo } from "../api/types";
import type { EngineResult } from "../hooks/useTypingEngine";
import { Sparkline } from "./Charts";
import { Button } from "./ui";
import "./results.css";

function fmtTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

interface Props {
  result: EngineResult;
  weakKeys: WeakKeyInfo[];
  saving: boolean;
  saveError: string | null;
  onNext: () => void;
  onRetry: () => void;
}

export function ResultsPanel({
  result,
  weakKeys,
  saving,
  saveError,
  onNext,
  onRetry,
}: Props) {
  const navigate = useNavigate();

  const stats = [
    { label: "WPM", value: Math.round(result.wpmNet).toString() },
    { label: "ACC", value: `${(result.accuracy * 100).toFixed(1)}%` },
    { label: "CONSISTENCY", value: `${(result.consistency * 100).toFixed(1)}%` },
    { label: "TIME", value: fmtTime(result.durationS) },
  ];

  return (
    <div className="tf-results-overlay">
      <div className="tf-results" role="dialog" aria-label="Session complete">
        <h2>Session Complete</h2>

        <div className="tf-results-stats">
          {stats.map((s) => (
            <div key={s.label} className="tf-result-stat">
              <div className="tf-result-value mono">{s.value}</div>
              <div className="tf-result-label">{s.label}</div>
            </div>
          ))}
        </div>

        {result.wpmSamples.length > 1 && (
          <div className="tf-results-spark">
            <Sparkline data={result.wpmSamples} />
          </div>
        )}

        {weakKeys.length > 0 && (
          <div className="tf-results-weak">
            <span className="tf-results-weak-label">Weakest keys:</span>{" "}
            {weakKeys.map((w, i) => (
              <span key={w.char} className="mono">
                {w.char}({(w.error_rate * 100).toFixed(0)}%)
                {i < weakKeys.length - 1 ? " · " : ""}
              </span>
            ))}
          </div>
        )}

        {saveError && <div className="tf-results-error">{saveError}</div>}
        {saving && <div className="tf-results-saving">Saving…</div>}

        <div className="tf-results-actions">
          <Button variant="primary" onClick={onNext}>
            Next Lesson
          </Button>
          <Button onClick={onRetry}>Try Again</Button>
          <Button variant="ghost" onClick={() => navigate("/dashboard")}>
            Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
