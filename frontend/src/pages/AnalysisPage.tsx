import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { lessonsApi, statsApi } from "../api/endpoints";
import { FerrisHeatmap } from "../components/FerrisHeatmap/FerrisHeatmap";
import { Card, Spinner } from "../components/ui";
import { useNavHotkeys } from "../hooks/useNavHotkeys";
import { useSettings } from "../stores/settingsStore";
import "./dashboard.css";

export function AnalysisPage() {
  useNavHotkeys();
  const layoutId = useSettings((s) => s.layoutId);
  const targetWpm = useSettings((s) => s.targetWpm);

  const heat = useQuery({
    queryKey: ["stats", "keys", layoutId],
    queryFn: () => statsApi.keys(layoutId),
  });
  const layouts = useQuery({
    queryKey: ["layouts"],
    queryFn: lessonsApi.layouts,
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

  return (
    <div className="tf-dash">
      <Card>
        <h3 className="tf-card-title">Key Heatmap — Accuracy</h3>
        <div className="tf-heatmap-center">
          {layoutInfo && (
            <FerrisHeatmap layout={layoutInfo} cells={cells} metric="error" />
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
        <div className="tf-heatmap-center">
          {layoutInfo && (
            <FerrisHeatmap
              layout={layoutInfo}
              cells={cells}
              metric="speed"
              target={targetWpm}
            />
          )}
        </div>
        <p className="tf-heat-legend">
          <span className="tf-heat-swatch tf-heat-swatch--good" /> at/above target
          ({targetWpm} WPM){"   "}
          <span className="tf-heat-swatch tf-heat-swatch--bad" /> slower
        </p>
      </Card>

      <Card>
        <h3 className="tf-card-title">Key Heatmap — Consistency</h3>
        <div className="tf-heatmap-center">
          {layoutInfo && (
            <FerrisHeatmap layout={layoutInfo} cells={cells} metric="consistency" />
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
