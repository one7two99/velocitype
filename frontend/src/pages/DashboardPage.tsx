import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { sessionsApi, statsApi } from "../api/endpoints";
import type { TrendPoint } from "../api/types";
import { TrendChart } from "../components/Charts";
import { Card, Spinner } from "../components/ui";
import { useNavHotkeys } from "../hooks/useNavHotkeys";
import { useSettings } from "../stores/settingsStore";
import "./dashboard.css";

function fmtPct(v: number | null) {
  return v == null ? "—" : `${(v * 100).toFixed(1)}%`;
}
function fmtNum(v: number | null) {
  return v == null ? "—" : Math.round(v).toString();
}

export function DashboardPage() {
  useNavHotkeys();
  const layoutId = useSettings((s) => s.layoutId);
  const targetWpm = useSettings((s) => s.targetWpm);

  const overview = useQuery({
    queryKey: ["stats", "overview", layoutId],
    queryFn: () => statsApi.overview(layoutId),
  });
  const heat = useQuery({
    queryKey: ["stats", "keys", layoutId],
    queryFn: () => statsApi.keys(layoutId),
  });
  const history = useQuery({
    queryKey: ["sessions", "history"],
    queryFn: () => sessionsApi.history(1, 10),
  });

  const trend: TrendPoint[] = useMemo(() => {
    const o = overview.data;
    if (!o) return [];
    const m = new Map<string, TrendPoint>();
    for (const p of o.wpm_trend)
      m.set(p.date, { date: p.date, wpm: p.wpm, accuracy: null });
    for (const p of o.accuracy_trend) {
      const e = m.get(p.date) ?? { date: p.date, wpm: null, accuracy: null };
      e.accuracy = p.accuracy;
      m.set(p.date, e);
    }
    return [...m.values()].sort((a, b) => a.date.localeCompare(b.date));
  }, [overview.data]);

  if (overview.isLoading) {
    return (
      <div className="tf-center">
        <Spinner />
      </div>
    );
  }

  const o = overview.data!;

  // Keys at target speed (keybr-style): key_wpm = 12000 / avg_latency_ms.
  const measuredKeys = (heat.data?.keys ?? []).filter(
    (k) => k.attempts >= 5 && k.avg_latency_ms,
  );
  const keysAtTarget = measuredKeys.filter(
    (k) => 12000 / (k.avg_latency_ms as number) >= targetWpm,
  ).length;

  const tiles = [
    { label: "Best WPM", value: fmtNum(o.best_wpm) },
    { label: "Avg WPM (30d)", value: fmtNum(o.avg_wpm_30d) },
    { label: "Avg Acc (30d)", value: fmtPct(o.avg_accuracy_30d) },
    { label: `Keys @ ${targetWpm}`, value: `${keysAtTarget}/${measuredKeys.length}` },
    { label: "Sessions", value: o.total_sessions.toString() },
    { label: "Time", value: `${Math.round(o.total_time_minutes)}m` },
  ];

  return (
    <div className="tf-dash">
      <div className="tf-tiles">
        {tiles.map((t) => (
          <Card key={t.label} className="tf-tile">
            <div className="tf-tile-value mono">{t.value}</div>
            <div className="tf-tile-label">{t.label}</div>
          </Card>
        ))}
      </div>

      <div className="tf-dash-grid">
        <Card>
          <h3 className="tf-card-title">30-Day Trend</h3>
          <TrendChart points={trend} target={targetWpm} />
        </Card>

        <Card>
          <h3 className="tf-card-title">Personal Bests</h3>
          <table className="tf-bests">
            <tbody>
              <tr>
                <td>Best WPM</td>
                <td className="mono">{fmtNum(o.best_wpm)}</td>
              </tr>
              <tr>
                <td>Best Accuracy</td>
                <td className="mono">{fmtPct(o.best_accuracy)}</td>
              </tr>
              <tr>
                <td>Best Consistency</td>
                <td className="mono">{fmtPct(o.best_consistency)}</td>
              </tr>
            </tbody>
          </table>
        </Card>
      </div>

      <Card>
        <h3 className="tf-card-title">Recent Sessions</h3>
        {history.data && history.data.items.length > 0 ? (
          <table className="tf-sessions">
            <thead>
              <tr>
                <th>Date</th>
                <th>Mode</th>
                <th>WPM</th>
                <th>Acc</th>
                <th>Consistency</th>
              </tr>
            </thead>
            <tbody>
              {history.data.items.map((s) => (
                <tr key={s.id}>
                  <td>{new Date(s.started_at).toLocaleString()}</td>
                  <td>
                    {s.mode === "coach_drill" ? (
                      <span className="tf-tag tf-tag--ai">AI Drill</span>
                    ) : (
                      s.mode
                    )}
                  </td>
                  <td className="mono">{fmtNum(s.wpm_net)}</td>
                  <td className="mono">{fmtPct(s.accuracy)}</td>
                  <td className="mono">{fmtPct(s.consistency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="tf-chart-empty">No sessions yet.</div>
        )}
      </Card>
    </div>
  );
}
