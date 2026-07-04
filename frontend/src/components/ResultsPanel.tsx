import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { WeakKeyInfo } from "../api/types";
import type { EngineResult } from "../hooks/useTypingEngine";
import { useSettings } from "../stores/settingsStore";
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

  // Results hotkeys: Enter -> Next Lesson, Space -> Try Again. Armed after a
  // short delay so the keystroke that just finished the lesson (e.g. a reflexive
  // Space after the last word) can't immediately trigger an action.
  useEffect(() => {
    let armed = false;
    const arm = setTimeout(() => {
      armed = true;
    }, 400);
    const onKey = (e: KeyboardEvent) => {
      if (!armed || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "Enter") {
        e.preventDefault();
        onNext();
      } else if (e.key === " " || e.code === "Space") {
        e.preventDefault();
        onRetry();
      } else if (e.key === "d" || e.key === "D") {
        e.preventDefault();
        navigate("/dashboard");
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(arm);
      document.removeEventListener("keydown", onKey);
    };
  }, [onNext, onRetry, navigate]);

  const targetWpm = useSettings((s) => s.targetWpm);
  const wpm = Math.round(result.wpmNet);
  const reachedTarget = result.wpmNet >= targetWpm;

  const stats = [
    { label: "WPM", value: wpm.toString() },
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
              {s.label === "WPM" && (
                <div
                  className={`tf-result-target${reachedTarget ? " tf-result-target--hit" : ""}`}
                >
                  {reachedTarget ? "✓ " : ""}target {targetWpm}
                </div>
              )}
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
            Next Lesson <kbd className="tf-kbd">Enter</kbd>
          </Button>
          <Button onClick={onRetry}>
            Try Again <kbd className="tf-kbd">Space</kbd>
          </Button>
          <Button variant="ghost" onClick={() => navigate("/dashboard")}>
            Dashboard <kbd className="tf-kbd">D</kbd>
          </Button>
        </div>
      </div>
    </div>
  );
}
