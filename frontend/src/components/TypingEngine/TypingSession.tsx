import { useQueryClient } from "@tanstack/react-query";
import { useTypingEngine, type EngineResult } from "../../hooks/useTypingEngine";
import { PaceIndicator } from "./PaceIndicator";
import { SessionProgressBar } from "./SessionProgressBar";
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

  // Lesson completion (used by the progress line in word-count mode).
  const totalChars = view.words.reduce((n, w) => n + w.length, 0) || 1;
  let typedChars = 0;
  for (let i = 0; i < view.wordIndex; i++) typedChars += view.words[i].length;
  typedChars += Math.min(view.charIndex, view.words[view.wordIndex]?.length ?? 0);
  const progress = Math.min(1, typedChars / totalChars);

  return (
    <div className="tf-session">
      <SessionProgressBar
        durationMs={durationMs}
        elapsedMs={view.elapsedMs}
        progress={progress}
      />
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
