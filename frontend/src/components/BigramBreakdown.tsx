import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { statsApi } from "../api/endpoints";
import type { NgramRow } from "../api/types";
import { Button, Card, Spinner } from "./ui";
import { useCoachStore } from "../stores/coachStore";
import { useSettings } from "../stores/settingsStore";
import "../pages/analysis.css";

type Status = "needs-data" | "error-prone" | "choppy" | "slow" | "on-target";
const STATUS_LABEL: Record<Status, string> = {
  "needs-data": "· needs data",
  "error-prone": "✗ error-prone",
  choppy: "〜 choppy",
  slow: "⚠ slow",
  "on-target": "✓ on-target",
};
const STATUS_RANK: Record<Status, number> = {
  "error-prone": 0, choppy: 1, slow: 2, "on-target": 3, "needs-data": 4,
};

const ERROR_PRONE_RATE = 0.08;
const CHOPPY_CONS = 0.7;
const MIN_ATTEMPTS = 8;
const MIN_LAT_N = 4;

interface BRow {
  ngram: string;
  cls: string | null;
  attempts: number;
  errPct: number;
  wpm: number | null;
  consistency: number | null;
  hitchPct: number | null;
  status: Status;
}

type SortKey = "ngram" | "cls" | "attempts" | "errPct" | "wpm" | "consistency" | "hitchPct" | "status";
const COLUMNS: { key: SortKey; label: string; num?: boolean }[] = [
  { key: "ngram", label: "Bigram" },
  { key: "cls", label: "Class" },
  { key: "attempts", label: "Att", num: true },
  { key: "errPct", label: "Err %", num: true },
  { key: "wpm", label: "WPM", num: true },
  { key: "consistency", label: "Cons %", num: true },
  { key: "hitchPct", label: "Hitch %", num: true },
  { key: "status", label: "Status" },
];

function toRow(r: NgramRow, target: number): BRow {
  const measured = r.attempts >= MIN_ATTEMPTS && r.latency_n >= MIN_LAT_N;
  let status: Status;
  if (!measured) status = "needs-data";
  else if (r.error_rate >= ERROR_PRONE_RATE) status = "error-prone";
  else if (r.consistency != null && r.consistency < CHOPPY_CONS) status = "choppy";
  else if (r.wpm != null && r.wpm < target) status = "slow";
  else status = "on-target";
  return {
    ngram: r.ngram,
    cls: r.cls,
    attempts: r.attempts,
    errPct: r.error_rate * 100,
    wpm: r.wpm,
    consistency: r.consistency,
    hitchPct: r.hitch_rate != null ? r.hitch_rate * 100 : null,
    status,
  };
}

function sortValue(r: BRow, key: SortKey): number | string | null {
  if (key === "status") return STATUS_RANK[r.status];
  return r[key];
}

export function BigramBreakdown() {
  const layoutId = useSettings((s) => s.layoutId);
  const targetWpm = useSettings((s) => s.targetWpm);
  const startBigramDrills = useCoachStore((s) => s.startBigramDrills);
  const navigate = useNavigate();

  const q = useQuery({
    queryKey: ["stats", "ngrams", layoutId],
    queryFn: () => statsApi.ngrams(layoutId),
  });

  const [sortKey, setSortKey] = useState<SortKey>("status");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [search, setSearch] = useState("");
  const [onlyWork, setOnlyWork] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!q.data) return;
    const needWork = q.data.ngrams
      .map((r) => toRow(r, targetWpm))
      .filter((r) => ["error-prone", "choppy", "slow"].includes(r.status))
      .map((r) => r.ngram);
    setSelected(new Set(needWork));
  }, [q.data, targetWpm]);

  const rows = useMemo(() => {
    const all = (q.data?.ngrams ?? []).map((r) => toRow(r, targetWpm));
    const term = search.trim().toLowerCase();
    let filtered = all;
    if (term) filtered = filtered.filter((r) => r.ngram.includes(term));
    if (onlyWork)
      filtered = filtered.filter((r) => ["error-prone", "choppy", "slow"].includes(r.status));
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const va = sortValue(a, sortKey);
      const vb = sortValue(b, sortKey);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return 0;
    });
  }, [q.data, targetWpm, search, onlyWork, sortKey, sortDir]);

  if (q.isLoading) {
    return (
      <Card>
        <h3 className="tf-card-title">Bigram breakdown</h3>
        <Spinner />
      </Card>
    );
  }

  const onSort = (key: SortKey) => {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir(key === "ngram" || key === "cls" || key === "status" ? "asc" : "desc");
    }
  };
  const fmt = (v: number | null, d = 0) => (v == null ? "—" : v.toFixed(d));

  const toggle = (n: string) =>
    setSelected((s) => {
      const next = new Set(s);
      next.has(n) ? next.delete(n) : next.add(n);
      return next;
    });
  const allSel = rows.length > 0 && rows.every((r) => selected.has(r.ngram));
  const toggleAll = () =>
    setSelected((s) => {
      const next = new Set(s);
      if (allSel) rows.forEach((r) => next.delete(r.ngram));
      else rows.forEach((r) => next.add(r.ngram));
      return next;
    });
  const generate = () => {
    if (selected.size) {
      startBigramDrills(Array.from(selected));
      navigate("/");
    }
  };

  const total = q.data?.ngrams.length ?? 0;

  return (
    <Card>
      <div className="tf-analysis-head">
        <h3 className="tf-card-title">Bigram breakdown</h3>
        <p className="tf-analysis-summary">{total} bigrams tracked · rhythm = consistency</p>
      </div>

      <div className="tf-keytable-controls">
        <input
          className="tf-input tf-keytable-search"
          placeholder="Search pair…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label className="tf-keytable-toggle">
          <input type="checkbox" checked={onlyWork} onChange={(e) => setOnlyWork(e.target.checked)} />
          only pairs needing work
        </label>
        <Button
          variant="primary"
          className="tf-drill-btn"
          disabled={selected.size === 0}
          onClick={generate}
        >
          Generate drill from {selected.size} bigram{selected.size === 1 ? "" : "s"}
        </Button>
      </div>

      {rows.length === 0 ? (
        <div className="tf-chart-empty">
          {total ? "No bigrams match your filter." : "No bigram data yet — type a few sessions."}
        </div>
      ) : (
        <div className="tf-keytable-wrap">
          <table className="tf-keytable">
            <thead>
              <tr>
                <th className="tf-check-col">
                  <input type="checkbox" aria-label="Select all" checked={allSel} onChange={toggleAll} />
                </th>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className={`${col.num ? "tf-num" : ""}${sortKey === col.key ? " tf-sorted" : ""}`}
                    onClick={() => onSort(col.key)}
                  >
                    {col.label}
                    {sortKey === col.key && (
                      <span className="tf-sort-caret">{sortDir === "asc" ? " ▲" : " ▼"}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.ngram}
                  className={`${selected.has(r.ngram) ? "tf-row-sel" : ""}${r.cls === "SFB" ? " tf-row-sfb" : ""}`}
                >
                  <td className="tf-check-col">
                    <input
                      type="checkbox"
                      aria-label={`Select ${r.ngram}`}
                      checked={selected.has(r.ngram)}
                      onChange={() => toggle(r.ngram)}
                    />
                  </td>
                  <td className="mono tf-key-cell">{r.ngram}</td>
                  <td>
                    {r.cls ? (
                      <span className={`tf-bg-class${r.cls === "SFB" ? " tf-bg-class--sfb" : ""}`}>
                        {r.cls}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="tf-num mono">{r.attempts}</td>
                  <td className="tf-num mono">{r.errPct.toFixed(1)}</td>
                  <td className="tf-num mono">{fmt(r.wpm)}</td>
                  <td className="tf-num mono">
                    {r.consistency == null ? "—" : (r.consistency * 100).toFixed(0)}
                  </td>
                  <td className="tf-num mono">{fmt(r.hitchPct)}</td>
                  <td>
                    <span className={`tf-status tf-status--${r.status}`}>{STATUS_LABEL[r.status]}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
