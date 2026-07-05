import { useQueryClient } from "@tanstack/react-query";
import { useTypingEngine, type EngineResult } from "../../hooks/useTypingEngine";
import { PaceIndicator } from "./PaceIndicator";
import { TypingText } from "./TypingText";
import "./typing-session.css";

function fmtTime(ms: number) {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;
}

export function TypingSession({
  lesson,
  onComplete,
  durationMs,
}: {
  lesson: string;
  onComplete: (r: EngineResult) => void;
  durationMs?: number;
}) {
  const qc = useQueryClient();
  const view = useTypingEngine(
    lesson,
    (r) => {
      // Stats will have changed after this session is saved.
      qc.invalidateQueries({ queryKey: ["stats"] });
      onComplete(r);
    },
    { durationMs },
  );

  // Timed mode shows a countdown; otherwise elapsed time.
  const timeMs = durationMs ? durationMs - view.elapsedMs : view.elapsedMs;

  return (
    <div className="tf-session">
      <div className="tf-metricsbar mono">
        <span>
          <b>{view.liveWpm}</b> wpm
        </span>
        <span>
          <b>{Math.round(view.liveAccuracy * 100)}</b>% acc
        </span>
        <span>
          <b>{fmtTime(timeMs)}</b>
          {durationMs ? " left" : ""}
        </span>
        <span className="tf-metrics-hint">Tab + Enter = restart</span>
      </div>

      <PaceIndicator avg={view.liveAvgWpm} now={view.liveWpm} />

      <div className="tf-typing-wrap" onClick={() => window.focus()}>
        <TypingText view={view} />
      </div>
    </div>
  );
}
