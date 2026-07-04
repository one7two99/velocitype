import { useMemo, useState } from "react";
import type { KeyHeatCell, LayoutInfo } from "../../api/types";
import { buildPositions, KEY_SIZE } from "./geometry";
import "./heatmap.css";

// error rate at which a key reaches full heat
const HEAT_CEIL = 0.3;

const DISPLAY: Record<string, string> = {
  " ": "␣",
  ";": ";",
  ",": ",",
  ".": ".",
  "/": "/",
};

interface Props {
  layout: LayoutInfo;
  cells: KeyHeatCell[];
  compact?: boolean;
}

export function FerrisHeatmap({ layout, cells, compact = false }: Props) {
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
        aria-label="Keyboard heatmap"
      >
        {keys.map((k) => {
          const cell = byChar.get(k.char);
          const rate = cell?.attempts ? cell.error_rate : 0;
          const intensity = Math.min(1, rate / HEAT_CEIL);
          return (
            <g
              key={k.char}
              transform={`translate(${k.x},${k.y})`}
              onMouseEnter={() =>
                cell &&
                setHover({ x: k.x, y: k.y, cell })
              }
              onMouseLeave={() => setHover(null)}
              style={{ cursor: cell?.attempts ? "pointer" : "default" }}
            >
              <rect
                width={KEY_SIZE}
                height={KEY_SIZE}
                rx={7}
                className="tf-key-base"
              />
              {intensity > 0 && (
                <rect
                  width={KEY_SIZE}
                  height={KEY_SIZE}
                  rx={7}
                  className="tf-key-heat"
                  style={{ opacity: 0.12 + intensity * 0.88 }}
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
          style={{
            left: hover.x + KEY_SIZE / 2,
            top: hover.y - 6,
          }}
        >
          <strong>{DISPLAY[hover.cell.character] ?? hover.cell.character}</strong>
          {" · "}
          {(hover.cell.error_rate * 100).toFixed(1)}% errors
          {hover.cell.avg_latency_ms != null && (
            <> · {Math.round(hover.cell.avg_latency_ms)}ms</>
          )}
        </div>
      )}
    </div>
  );
}
