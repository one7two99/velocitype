import "./pace-indicator.css";

// Half-span of the diverging scale, in WPM. The centre is the session average;
// the dot shows how far the rolling 10s pace deviates from it.
const SPAN = 30;

export function PaceIndicator({ avg, now }: { avg: number; now: number }) {
  const hasData = avg > 0;
  const delta = now - avg;
  const clamped = Math.max(-1, Math.min(1, delta / SPAN));
  const pos = 50 + clamped * 50; // percent from left; 50% = average

  const state = !hasData || Math.abs(delta) < 1 ? "even" : delta > 0 ? "up" : "down";

  return (
    <div className="tf-pace" aria-label="pace vs average">
      <span className="tf-pace-side">slower ◄</span>
      <div className="tf-pace-track">
        <div className="tf-pace-mid" />
        {hasData && (
          <div
            className={`tf-pace-dot tf-pace-dot--${state}`}
            style={{ left: `${pos}%` }}
          />
        )}
        <span className="tf-pace-avg mono">{hasData ? `Ø ${avg}` : "Ø —"}</span>
      </div>
      <span className="tf-pace-side">► faster</span>
      <span className={`tf-pace-delta mono tf-pace-delta--${state}`}>
        {hasData ? `${delta >= 0 ? "+" : "−"}${Math.abs(delta)}` : ""}
      </span>
    </div>
  );
}
