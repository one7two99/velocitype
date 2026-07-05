import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { lessonsApi, statsApi } from "../api/endpoints";
import { FerrisHeatmap } from "../components/FerrisHeatmap/FerrisHeatmap";
import { Card, Spinner } from "../components/ui";
import { useNavHotkeys } from "../hooks/useNavHotkeys";
import { useSettings } from "../stores/settingsStore";
import "./dashboard.css";
import "./settings.css";

export function HeatmapsPage() {
  useNavHotkeys();
  const layoutId = useSettings((s) => s.layoutId);
  const targetWpm = useSettings((s) => s.targetWpm);
  // Local, explorable WPM threshold for the Speed heatmap (starts at the target).
  const [threshold, setThreshold] = useState(targetWpm);

  const heat = useQuery({
    queryKey: ["stats", "keys", layoutId],
    queryFn: () => statsApi.keys(layoutId),
  });
  const layouts = useQuery({
    queryKey: ["layouts"],
    queryFn: lessonsApi.layouts,
  });
  const unlock = useQuery({
    queryKey: ["lessons", "unlock", layoutId],
    queryFn: () => lessonsApi.unlock(layoutId),
  });

  const layoutInfo = useMemo(
    () =>
      layouts.data?.layouts.find((l) => l.id === layoutId) ??
      layouts.data?.layouts[0],
    [layouts.data, layoutId],
  );

  if (layouts.isLoading || heat.isLoading) {
    return (
      <div className="tf-center">
        <Spinner />
      </div>
    );
  }

  const cells = heat.data?.keys ?? [];
  // Locked-key overlay only when progressive unlocking is active.
  const unlockedKeys =
    unlock.data?.progressive ? unlock.data.unlocked : undefined;

  // How many measured keys reach the chosen WPM threshold.
  const measured = cells.filter((k) => k.attempts >= 5 && k.avg_latency_ms);
  const reached = measured.filter(
    (k) => 12000 / (k.avg_latency_ms as number) >= threshold,
  ).length;

  return (
    <div className="tf-dash">
      {unlock.data?.progressive && (
        <Card>
          <p className="tf-settings-note">
            🔓 Progressive unlocking — <b className="mono">{unlock.data.unlocked_count}</b>
            /{unlock.data.total} keys unlocked
            {unlock.data.next_char
              ? ` · next: ${unlock.data.next_char === " " ? "␣" : unlock.data.next_char}`
              : " · all keys unlocked!"}
          </p>
        </Card>
      )}
      <Card>
        <h3 className="tf-card-title">Key Heatmap — Accuracy</h3>
        <div className="tf-heatmap-center">
          {layoutInfo && (
            <FerrisHeatmap layout={layoutInfo} cells={cells} metric="error" unlocked={unlockedKeys} />
          )}
        </div>
        <p className="tf-heat-legend">
          <span className="tf-heat-swatch tf-heat-swatch--bad" /> more errors
          {"   "}
          <span className="tf-heat-swatch tf-heat-swatch--good" /> accurate
        </p>
      </Card>

      <Card>
        <h3 className="tf-card-title">Key Heatmap — Speed</h3>
        <div className="tf-analysis-slider">
          <label htmlFor="tf-wpm-threshold">
            Show keys reaching <b className="mono">{threshold}</b> WPM
          </label>
          <div className="tf-range-row">
            <input
              id="tf-wpm-threshold"
              type="range"
              className="tf-range"
              min={20}
              max={150}
              step={5}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
            />
            <span className="tf-range-value mono">
              {reached}/{measured.length}
            </span>
          </div>
        </div>
        <div className="tf-heatmap-center">
          {layoutInfo && (
            <FerrisHeatmap
              layout={layoutInfo}
              cells={cells}
              metric="speed"
              target={threshold}
              unlocked={unlockedKeys}
            />
          )}
        </div>
        <p className="tf-heat-legend">
          <span className="tf-heat-swatch tf-heat-swatch--good" /> at/above{" "}
          {threshold} WPM{"   "}
          <span className="tf-heat-swatch tf-heat-swatch--bad" /> slower
        </p>
      </Card>

      <Card>
        <h3 className="tf-card-title">Key Heatmap — Consistency</h3>
        <div className="tf-heatmap-center">
          {layoutInfo && (
            <FerrisHeatmap layout={layoutInfo} cells={cells} metric="consistency" unlocked={unlockedKeys} />
          )}
        </div>
        <p className="tf-heat-legend">
          <span className="tf-heat-swatch tf-heat-swatch--good" /> steady timing
          {"   "}
          <span className="tf-heat-swatch tf-heat-swatch--bad" /> erratic
        </p>
      </Card>
    </div>
  );
}
