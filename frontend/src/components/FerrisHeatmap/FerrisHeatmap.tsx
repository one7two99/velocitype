import { useMemo, useState } from "react";
import type { KeyHeatCell, LayoutInfo } from "../../api/types";
import { buildPositions, KEY_SIZE } from "./geometry";
import "./heatmap.css";

// error rate at which a key reaches full heat
const HEAT_CEIL = 0.3;
// minimum attempts before a key's speed is considered meaningful
const SPEED_MIN_ATTEMPTS = 5;
// inconsistency (1 - consistency) at which a key reaches full heat
const CONS_CEIL = 0.4;

export type HeatMetric = "error" | "speed" | "consistency";

const DISPLAY: Record<string, string> = {
  " ": "␣",
  ";": ";",
  ",": ",",
  ".": ".",
  "/": "/",
};

function keyWpm(cell: KeyHeatCell): number | null {
  if (!cell.avg_latency_ms || cell.avg_latency_ms <= 0) return null;
  return 12000 / cell.avg_latency_ms;
}

// Per-key overlay colour. Returns null for keys without meaningful data (neutral).
function overlayFor(
  cell: KeyHeatCell | undefined,
  metric: HeatMetric,
  target: number,
): { fill: string; opacity: number } | null {
  if (!cell || cell.attempts <= 0) return null;

  if (metric === "error") {
    const intensity = Math.min(1, cell.error_rate / HEAT_CEIL);
    if (intensity <= 0) return { fill: "var(--correct)", opacity: 0.25 };
    return { fill: "var(--heat-max)", opacity: 0.12 + intensity * 0.88 };
  }

  if (metric === "consistency") {
    // Higher consistency = green; erratic = red (mirrors the accuracy metric).
    if (cell.consistency == null) return null;
    const badness = 1 - cell.consistency;
    const intensity = Math.min(1, badness / CONS_CEIL);
    if (intensity <= 0) return { fill: "var(--correct)", opacity: 0.35 };
    if (cell.consistency >= 0.9) return { fill: "var(--correct)", opacity: 0.35 };
    return { fill: "var(--heat-max)", opacity: 0.12 + intensity * 0.88 };
  }

  // speed: green at/above target, red below (keybr-style)
  const kw = keyWpm(cell);
  if (kw === null || cell.attempts < SPEED_MIN_ATTEMPTS) return null;
  const ratio = kw / target;
  if (ratio >= 1) {
    return { fill: "var(--correct)", opacity: 0.35 + Math.min(1, (ratio - 1) / 0.5) * 0.5 };
  }
  return { fill: "var(--heat-max)", opacity: 0.12 + (1 - ratio) * 0.88 };
}

function tooltipFor(cell: KeyHeatCell, metric: HeatMetric, target: number): string {
  if (metric === "speed") {
    const kw = keyWpm(cell);
    return kw === null
      ? `no speed data · target ${target}`
      : `${Math.round(kw)} wpm · target ${target}`;
  }
  if (metric === "consistency") {
    return cell.consistency == null
      ? "not enough data"
      : `${Math.round(cell.consistency * 100)}% consistency`;
  }
  const ms = cell.avg_latency_ms != null ? ` · ${Math.round(cell.avg_latency_ms)}ms` : "";
  return `${(cell.error_rate * 100).toFixed(1)}% errors${ms}`;
}

interface Props {
  layout: LayoutInfo;
  cells: KeyHeatCell[];
  metric?: HeatMetric;
  target?: number;
  compact?: boolean;
}

export function FerrisHeatmap({
  layout,
  cells,
  metric = "error",
  target = 40,
  compact = false,
}: Props) {
  const { keys, width, height, thumbs } = useMemo(
    () => buildPositions(layout),
    [layout],
  );
  const byChar = useMemo(() => {
    const m = new Map<string, KeyHeatCell>();
    for (const c of cells) m.set(c.character, c);
    return m;
  }, [cells]);

  const [hover, setHover] = useState<{
    x: number;
    y: number;
    cell: KeyHeatCell;
  } | null>(null);

  const scale = compact ? 0.62 : 1;

  return (
    <div className="tf-heatmap" style={{ position: "relative" }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width={width * scale}
        height={height * scale}
        role="img"
        aria-label={`Keyboard heatmap by ${metric}`}
      >
        {keys.map((k) => {
          // Non-trainable modifier keys (Corne outer columns): greyed, inert.
          if (k.deco) {
            return (
              <g key={`${k.hand}-${k.x}-${k.y}`} transform={`translate(${k.x},${k.y})`}>
                <rect
                  width={KEY_SIZE}
                  height={KEY_SIZE}
                  rx={7}
                  className="tf-key-deco"
                />
                <text
                  x={KEY_SIZE / 2}
                  y={KEY_SIZE / 2}
                  className="tf-key-deco-label"
                  dominantBaseline="central"
                  textAnchor="middle"
                >
                  {k.label.length > 3 ? k.label.slice(0, 3) : k.label}
                </text>
              </g>
            );
          }
          const cell = byChar.get(k.char);
          const overlay = overlayFor(cell, metric, target);
          return (
            <g
              key={k.char}
              transform={`translate(${k.x},${k.y})`}
              onMouseEnter={() => cell && setHover({ x: k.x, y: k.y, cell })}
              onMouseLeave={() => setHover(null)}
              style={{ cursor: cell?.attempts ? "pointer" : "default" }}
            >
              <rect width={KEY_SIZE} height={KEY_SIZE} rx={7} className="tf-key-base" />
              {overlay && (
                <rect
                  width={KEY_SIZE}
                  height={KEY_SIZE}
                  rx={7}
                  className="tf-key-overlay"
                  style={{ fill: overlay.fill, opacity: overlay.opacity }}
                />
              )}
              <text
                x={KEY_SIZE / 2}
                y={KEY_SIZE / 2}
                className="tf-key-label"
                dominantBaseline="central"
                textAnchor="middle"
              >
                {DISPLAY[k.char] ?? k.char}
              </text>
            </g>
          );
        })}

        {thumbs.map((t, i) =>
          t.label ? (
            <g key={i} transform={`translate(${t.x},${t.y})`}>
              <rect
                width={KEY_SIZE}
                height={KEY_SIZE}
                rx={KEY_SIZE / 2}
                className="tf-key-thumb"
              />
              <text
                x={KEY_SIZE / 2}
                y={KEY_SIZE / 2}
                className="tf-key-thumb-label"
                dominantBaseline="central"
                textAnchor="middle"
              >
                {t.label.slice(0, 3)}
              </text>
            </g>
          ) : null,
        )}
      </svg>

      {hover && !compact && (
        <div
          className="tf-heat-tooltip mono"
          style={{ left: hover.x + KEY_SIZE / 2, top: hover.y - 6 }}
        >
          <strong>{DISPLAY[hover.cell.character] ?? hover.cell.character}</strong>
          {" · "}
          {tooltipFor(hover.cell, metric, target)}
        </div>
      )}
    </div>
  );
}
