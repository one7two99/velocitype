import "./session-progress.css";

// A thin session-progress line. Timed mode: a countdown that depletes
// (full → empty), turning warm near the end. Word-count mode: fills up with
// lesson completion. Smoothed via a CSS transition over the engine's 500ms tick.
export function SessionProgressBar({
  durationMs,
  elapsedMs,
  progress,
}: {
  durationMs?: number;
  elapsedMs: number;
  progress: number;
}) {
  const timed = !!durationMs;
  const remaining = timed
    ? Math.max(0, Math.min(1, 1 - elapsedMs / (durationMs as number)))
    : 0;
  const fill = timed ? remaining : Math.max(0, Math.min(1, progress));
  const warn = timed && remaining < 0.15;

  return (
    <div
      className="tf-progress"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(fill * 100)}
    >
      <div
        className={`tf-progress-fill${warn ? " tf-progress-fill--warn" : ""}`}
        style={{ width: `${fill * 100}%` }}
      />
    </div>
  );
}
