import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { coachApi } from "../api/endpoints";
import { Alert, Button, Card, Spinner } from "../components/ui";
import { useNavHotkeys } from "../hooks/useNavHotkeys";
import { useCoachStore } from "../stores/coachStore";
import { useSettings } from "../stores/settingsStore";
import "./coach.css";

function errText(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Something went wrong.";
}

function fmtNum(v: number | null) {
  return v == null ? "—" : Math.round(v).toString();
}
function fmtPct(v: number | null) {
  return v == null ? "—" : `${(v * 100).toFixed(1)}%`;
}

export function CoachPage() {
  useNavHotkeys();
  const layoutId = useSettings((s) => s.layoutId);
  const drillActive = useCoachStore((s) => s.drillActive);
  const startDrills = useCoachStore((s) => s.startDrills);
  const stopDrills = useCoachStore((s) => s.stopDrills);
  const navigate = useNavigate();

  const status = useQuery({
    queryKey: ["coach", "status"],
    queryFn: coachApi.status,
    refetchInterval: (q) => (q.state.data?.model_ready ? false : 5000),
  });

  const metrics = useQuery({
    queryKey: ["coach", "metrics", layoutId],
    queryFn: () => coachApi.metrics(layoutId),
  });

  const analyze = useMutation({
    mutationFn: () => coachApi.analyze(layoutId),
  });

  const modelReady = status.data?.model_ready;
  const reachable = status.data?.reachable;
  const isMistral = status.data?.provider === "mistral";

  return (
    <div className="tf-coach">
      {/* Transparency: exactly the numbers the coach uses */}
      <Card>
        <h3 className="tf-card-title">What your coach sees</h3>
        {metrics.isLoading ? (
          <Spinner />
        ) : metrics.data ? (
          <>
            <div className="tf-coach-metrics">
              <div>
                <span className="tf-coach-m-label">Avg WPM (30d)</span>
                <span className="tf-coach-m-value mono">
                  {fmtNum(metrics.data.lifetime.avg_wpm_30d)}
                </span>
              </div>
              <div>
                <span className="tf-coach-m-label">Avg accuracy (30d)</span>
                <span className="tf-coach-m-value mono">
                  {fmtPct(metrics.data.lifetime.avg_accuracy_30d)}
                </span>
              </div>
              <div>
                <span className="tf-coach-m-label">Best WPM</span>
                <span className="tf-coach-m-value mono">
                  {fmtNum(metrics.data.lifetime.best_wpm)}
                </span>
              </div>
              <div>
                <span className="tf-coach-m-label">Sessions</span>
                <span className="tf-coach-m-value mono">
                  {metrics.data.lifetime.sessions}
                </span>
              </div>
            </div>
            <div className="tf-coach-weak">
              <span className="tf-coach-m-label">Weak keys:</span>{" "}
              {metrics.data.weak_keys.length ? (
                metrics.data.weak_keys.map((w) => (
                  <span key={w.char} className="mono tf-coach-weakkey">
                    {w.char} {(w.error_rate * 100).toFixed(0)}%
                    {w.avg_latency_ms != null ? `/${Math.round(w.avg_latency_ms)}ms` : ""}
                  </span>
                ))
              ) : (
                <span className="tf-coach-m-label">none yet — type a few sessions</span>
              )}
            </div>
          </>
        ) : (
          <div className="tf-chart-empty">No metrics yet.</div>
        )}
      </Card>

      {/* Model + actions */}
      <Card>
        <h3 className="tf-card-title">AI Coach</h3>
        <p className="tf-settings-note">
          {isMistral ? (
            <>
              Coaching runs on Mistral (EU cloud)
              {status.data ? ` (${status.data.model})` : ""} — your stats are sent to
              Mistral. Switch to local Ollama in Settings for full privacy.
            </>
          ) : (
            <>
              Coaching runs on a local Ollama model
              {status.data ? ` (${status.data.model})` : ""} — nothing leaves your machine.
            </>
          )}
        </p>

        {status.isLoading ? (
          <Spinner />
        ) : !reachable ? (
          isMistral ? (
            <Alert>
              Mistral isn't reachable. Set a valid API key in Settings → AI Provider.
            </Alert>
          ) : (
            <Alert>
              Local model server not reachable. Is the <code>ollama</code> service running?
            </Alert>
          )
        ) : !modelReady ? (
          <div className="tf-coach-status">
            <Spinner />
            <span>
              Model is still downloading on the server. This page will enable
              automatically when it's ready.
            </span>
          </div>
        ) : (
          <div className="tf-coach-actions">
            <Button
              variant="primary"
              onClick={() => analyze.mutate()}
              disabled={analyze.isPending}
            >
              {analyze.isPending ? "Analyzing…" : "Get analysis"}
            </Button>
            {drillActive ? (
              <>
                <Button onClick={() => navigate("/")}>Go to Trainer</Button>
                <Button variant="ghost" onClick={() => stopDrills()}>
                  Stop drills
                </Button>
                <span className="tf-coach-active mono">● drills active</span>
              </>
            ) : (
              <Button
                onClick={() => {
                  startDrills([]);
                  navigate("/");
                }}
              >
                Start coaching drills
              </Button>
            )}
          </div>
        )}

        {analyze.isPending && (
          <p className="tf-coach-hint">
            Local generation can take up to a minute or two on CPU — hang tight.
          </p>
        )}
      </Card>

      {analyze.isError && <Alert>{errText(analyze.error)}</Alert>}

      {analyze.data && (
        <Card>
          <h3 className="tf-card-title">Analysis</h3>
          <p className="tf-coach-analysis">{analyze.data.analysis}</p>
        </Card>
      )}
    </div>
  );
}
