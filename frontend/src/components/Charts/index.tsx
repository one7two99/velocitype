import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendPoint } from "../../api/types";

const AXIS = "#6b7280";
const GRID = "#2a2f42";
const WPM = "#e8c547";
const ACC = "#4ade80";

function fmtDate(d: string) {
  return d.slice(5); // MM-DD
}

export function TrendChart({ points }: { points: TrendPoint[] }) {
  const data = points.map((p) => ({
    date: fmtDate(p.date),
    wpm: p.wpm ?? null,
    accuracy: p.accuracy != null ? Math.round(p.accuracy * 1000) / 10 : null,
  }));

  if (data.length === 0) {
    return <div className="tf-chart-empty">No sessions yet — start typing.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="date" stroke={AXIS} fontSize={12} tickMargin={8} />
        <YAxis
          yAxisId="wpm"
          stroke={AXIS}
          fontSize={12}
          width={38}
          domain={[0, "auto"]}
        />
        <YAxis
          yAxisId="acc"
          orientation="right"
          stroke={AXIS}
          fontSize={12}
          width={40}
          domain={[0, 100]}
          unit="%"
        />
        <Tooltip
          contentStyle={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: "var(--text-muted)" }}
        />
        <Line
          yAxisId="wpm"
          type="monotone"
          dataKey="wpm"
          name="WPM"
          stroke={WPM}
          strokeWidth={2}
          dot={false}
          connectNulls
        />
        <Line
          yAxisId="acc"
          type="monotone"
          dataKey="accuracy"
          name="Accuracy %"
          stroke={ACC}
          strokeWidth={2}
          dot={false}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function Sparkline({ data }: { data: number[] }) {
  const points = data.map((v, i) => ({ i, v: Math.round(v) }));
  if (points.length < 2) return null;
  return (
    <ResponsiveContainer width="100%" height={60}>
      <LineChart data={points} margin={{ top: 6, right: 4, left: 4, bottom: 0 }}>
        <Line
          type="monotone"
          dataKey="v"
          stroke={WPM}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
