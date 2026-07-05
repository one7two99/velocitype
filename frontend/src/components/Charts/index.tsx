import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SessionStatPoint, TrendPoint } from "../../api/types";

const AXIS = "#6b7280";
const GRID = "#2a2f42";
const WPM = "#e8c547";
const ACC = "#4ade80";
const MAXWPM = "#fb923c";
const KEYS = "#5b6478";

function fmtDate(d: string) {
  return d.slice(5); // MM-DD
}

export function TrendChart({
  points,
  target,
}: {
  points: TrendPoint[];
  target?: number;
}) {
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
        {target ? (
          <ReferenceLine
            yAxisId="wpm"
            y={target}
            stroke={WPM}
            strokeDasharray="4 4"
            strokeOpacity={0.6}
            label={{ value: `target ${target}`, position: "insideTopRight", fill: AXIS, fontSize: 11 }}
          />
        ) : null}
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

export function SessionsChart({
  points,
  target,
}: {
  points: SessionStatPoint[];
  target?: number;
}) {
  const data = points.map((p) => ({
    idx: p.index,
    date: new Date(p.started_at).toLocaleString(),
    keys: p.distinct_keys,
    avg: p.avg_wpm ?? null,
    max: p.max_wpm ?? null,
    acc: p.accuracy != null ? Math.round(p.accuracy * 1000) / 10 : null,
  }));

  if (data.length === 0) {
    return (
      <div className="tf-chart-empty">
        No completed sessions yet — finish a session to see it here.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="idx" stroke={AXIS} fontSize={12} tickMargin={8} />
        {/* Distinct-keys count: its own hidden axis so the bars read as context
            behind the speed/accuracy lines rather than distorting their scale. */}
        <YAxis yAxisId="keys" hide domain={[0, "dataMax"]} />
        <YAxis yAxisId="wpm" stroke={AXIS} fontSize={12} width={38} domain={[0, "auto"]} />
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
          labelFormatter={(_, payload) =>
            payload && payload.length ? payload[0].payload.date : ""
          }
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {target ? (
          <ReferenceLine
            yAxisId="wpm"
            y={target}
            stroke={WPM}
            strokeDasharray="4 4"
            strokeOpacity={0.5}
            label={{ value: `target ${target}`, position: "insideTopRight", fill: AXIS, fontSize: 11 }}
          />
        ) : null}
        <Bar
          yAxisId="keys"
          dataKey="keys"
          name="Keys"
          fill={KEYS}
          fillOpacity={0.5}
          maxBarSize={18}
          isAnimationActive={false}
        />
        <Line
          yAxisId="wpm"
          type="monotone"
          dataKey="avg"
          name="Avg WPM"
          stroke={WPM}
          strokeWidth={2}
          dot={false}
          connectNulls
        />
        <Line
          yAxisId="wpm"
          type="monotone"
          dataKey="max"
          name="Max WPM"
          stroke={MAXWPM}
          strokeWidth={2}
          strokeDasharray="5 3"
          dot={false}
          connectNulls
        />
        <Line
          yAxisId="acc"
          type="monotone"
          dataKey="acc"
          name="Accuracy %"
          stroke={ACC}
          strokeWidth={2}
          dot={false}
          connectNulls
        />
      </ComposedChart>
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
