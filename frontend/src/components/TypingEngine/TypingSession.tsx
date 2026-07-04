import { useQueryClient } from "@tanstack/react-query";
import { useTypingEngine, type EngineResult } from "../../hooks/useTypingEngine";
import { TypingText } from "./TypingText";
import "./typing-session.css";

function fmtTime(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;
}

export function TypingSession({
  lesson,
  onComplete,
}: {
  lesson: string;
  onComplete: (r: EngineResult) => void;
}) {
  const qc = useQueryClient();
  const view = useTypingEngine(lesson, (r) => {
    // Stats will have changed after this session is saved.
    qc.invalidateQueries({ queryKey: ["stats"] });
    onComplete(r);
  });

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
          <b>{fmtTime(view.elapsedMs)}</b>
        </span>
        <span className="tf-metrics-hint">Tab + Enter = restart</span>
      </div>

      <div className="tf-typing-wrap" onClick={() => window.focus()}>
        <TypingText view={view} />
      </div>
    </div>
  );
}
