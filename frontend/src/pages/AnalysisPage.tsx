import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { statsApi } from "../api/endpoints";
import type { KeyHeatCell } from "../api/types";
import { Card, Spinner } from "../components/ui";
import { useNavHotkeys } from "../hooks/useNavHotkeys";
import { useSettings } from "../stores/settingsStore";
import "./dashboard.css";
import "./analysis.css";

const DISPLAY: Record<string, string> = { " ": "␣" };
const disp = (c: string) => DISPLAY[c] ?? c;

type Status = "needs-data" | "error-prone" | "slow" | "on-target";
const STATUS_LABEL: Record<Status, string> = {
  "needs-data": "· needs data",
  "error-prone": "✗ error-prone",
  slow: "⚠ slow",
  "on-target": "✓ on-target",
};
// Ordering used for the default "needs work first" sort.
const STATUS_RANK: Record<Status, number> = {
  "error-prone": 0,
  slow: 1,
  "on-target": 2,
  "needs-data": 3,
};

const ERROR_PRONE_RATE = 0.08; // ≥8% errors → flagged

interface Row {
  char: string;
  hand: string | null;
  finger: string | null;
  attempts: number;
  errors: number;
  errPct: number;
  wpm: number | null;
  latency: number | null;
  consistency: number | null;
  status: Status;
}

type SortKey =
  | "char" | "hand" | "finger" | "attempts" | "errors"
  | "errPct" | "wpm" | "latency" | "consistency" | "status";

const COLUMNS: { key: SortKey; label: string; num?: boolean }[] = [
  { key: "char", label: "Key" },
  { key: "hand", label: "Hand" },
  { key: "finger", label: "Finger" },
  { key: "attempts", label: "Att", num: true },
  { key: "errors", label: "Err", num: true },
  { key: "errPct", label: "Err %", num: true },
  { key: "wpm", label: "WPM", num: true },
  { key: "latency", label: "Lat (ms)", num: true },
  { key: "consistency", label: "Cons %", num: true },
  { key: "status", label: "Status" },
];

function toRow(c: KeyHeatCell, target: number): Row {
  const wpm = c.avg_latency_ms ? 12000 / c.avg_latency_ms : null;
  const measured = c.attempts >= 5 && c.avg_latency_ms != null;
  let status: Status;
  if (!measured) status = "needs-data";
  else if (c.error_rate >= ERROR_PRONE_RATE) status = "error-prone";
  else if (wpm != null && wpm < target) status = "slow";
  else status = "on-target";
  return {
    char: c.character,
    hand: c.hand,
    finger: c.finger,
    attempts: c.attempts,
    errors: c.errors,
    errPct: c.error_rate * 100,
    wpm,
    latency: c.avg_latency_ms,
    consistency: c.consistency,
    status,
  };
}

function sortValue(r: Row, key: SortKey): number | string | null {
  if (key === "status") return STATUS_RANK[r.status];
  return r[key];
}

export function AnalysisPage() {
  useNavHotkeys();
  const layoutId = useSettings((s) => s.layoutId);
  const targetWpm = useSettings((s) => s.targetWpm);

  const heat = useQuery({
    queryKey: ["stats", "keys", layoutId],
    queryFn: () => statsApi.keys(layoutId),
  });

  const [sortKey, setSortKey] = useState<SortKey>("errPct");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [search, setSearch] = useState("");
  const [onlyWork, setOnlyWork] = useState(false);

  const rows = useMemo(() => {
    const all = (heat.data?.keys ?? [])
      .filter((c) => c.attempts > 0)
      .map((c) => toRow(c, targetWpm));
    const q = search.trim().toLowerCase();
    let filtered = all;
    if (q) filtered = filtered.filter((r) => r.char.toLowerCase().includes(q));
    if (onlyWork)
      filtered = filtered.filter(
        (r) => r.status === "error-prone" || r.status === "slow",
      );
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const va = sortValue(a, sortKey);
      const vb = sortValue(b, sortKey);
      // Nulls (unmeasured) always sort last, regardless of direction.
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return 0;
    });
  }, [heat.data, targetWpm, search, onlyWork, sortKey, sortDir]);

  const summary = useMemo(() => {
    const cells = heat.data?.keys ?? [];
    const tracked = cells.filter((c) => c.attempts > 0).length;
    const measured = cells.filter((c) => c.attempts >= 5 && c.avg_latency_ms);
    const reached = measured.filter(
      (c) => 12000 / (c.avg_latency_ms as number) >= targetWpm,
    ).length;
    return { tracked, measured: measured.length, reached };
  }, [heat.data, targetWpm]);

  if (heat.isLoading) {
    return (
      <div className="tf-center">
        <Spinner />
      </div>
    );
  }

  const onSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      // Text columns default to ascending; numeric to descending (worst first).
      setSortDir(key === "char" || key === "hand" || key === "finger" ? "asc" : "desc");
    }
  };

  const fmtNum = (v: number | null, digits = 0) =>
    v == null ? "—" : v.toFixed(digits);

  return (
    <div className="tf-dash">
      <Card>
        <div className="tf-analysis-head">
          <h3 className="tf-card-title">Per-key breakdown</h3>
          <p className="tf-analysis-summary">
            {summary.tracked} keys tracked · {summary.reached}/{summary.measured}{" "}
            reach {targetWpm} WPM
          </p>
        </div>

        <div className="tf-keytable-controls">
          <input
            className="tf-input tf-keytable-search"
            placeholder="Search key…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <label className="tf-keytable-toggle">
            <input
              type="checkbox"
              checked={onlyWork}
              onChange={(e) => setOnlyWork(e.target.checked)}
            />
            only keys needing work
          </label>
        </div>

        {rows.length === 0 ? (
          <div className="tf-chart-empty">
            {heat.data?.keys?.length
              ? "No keys match your filter."
              : "No key data yet — type a few sessions."}
          </div>
        ) : (
          <div className="tf-keytable-wrap">
            <table className="tf-keytable">
              <thead>
                <tr>
                  {COLUMNS.map((col) => (
                    <th
                      key={col.key}
                      className={`${col.num ? "tf-num" : ""}${
                        sortKey === col.key ? " tf-sorted" : ""
                      }`}
                      onClick={() => onSort(col.key)}
                    >
                      {col.label}
                      {sortKey === col.key && (
                        <span className="tf-sort-caret">
                          {sortDir === "asc" ? " ▲" : " ▼"}
                        </span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.char}>
                    <td className="mono tf-key-cell">{disp(r.char)}</td>
                    <td>{r.hand ?? "—"}</td>
                    <td>{r.finger ?? "—"}</td>
                    <td className="tf-num mono">{r.attempts}</td>
                    <td className="tf-num mono">{r.errors}</td>
                    <td className="tf-num mono">{r.errPct.toFixed(1)}</td>
                    <td className="tf-num mono">{fmtNum(r.wpm)}</td>
                    <td className="tf-num mono">{fmtNum(r.latency)}</td>
                    <td className="tf-num mono">
                      {r.consistency == null ? "—" : (r.consistency * 100).toFixed(0)}
                    </td>
                    <td>
                      <span className={`tf-status tf-status--${r.status}`}>
                        {STATUS_LABEL[r.status]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
