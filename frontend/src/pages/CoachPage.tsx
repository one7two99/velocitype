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

export function CoachPage() {
  useNavHotkeys();
  const layoutId = useSettings((s) => s.layoutId);
  const setPendingDrill = useCoachStore((s) => s.setPendingDrill);
  const navigate = useNavigate();

  const status = useQuery({
    queryKey: ["coach", "status"],
    queryFn: coachApi.status,
    refetchInterval: (q) =>
      q.state.data?.model_ready ? false : 5000, // poll while the model downloads
  });

  const analyze = useMutation({
    mutationFn: () => coachApi.analyze(layoutId),
  });

  const drill = useMutation({
    mutationFn: () => coachApi.drill(layoutId),
    onSuccess: (data) => {
      setPendingDrill(data.lesson);
      navigate("/");
    },
  });

  const modelReady = status.data?.model_ready;
  const reachable = status.data?.reachable;

  return (
    <div className="tf-coach">
      <Card>
        <h3 className="tf-card-title">AI Coach</h3>
        <p className="tf-settings-note">
          Coaching runs on a local Ollama model
          {status.data ? ` (${status.data.model})` : ""} — nothing leaves your
          machine.
        </p>

        {status.isLoading ? (
          <Spinner />
        ) : !reachable ? (
          <Alert>
            Local model server not reachable. Is the <code>ollama</code> service
            running?
          </Alert>
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
            <Button onClick={() => drill.mutate()} disabled={drill.isPending}>
              {drill.isPending ? "Generating…" : "Generate drill & start"}
            </Button>
          </div>
        )}

        {(analyze.isPending || drill.isPending) && (
          <p className="tf-coach-hint">
            Local generation can take up to a minute or two on CPU — hang tight.
          </p>
        )}
      </Card>

      {analyze.isError && <Alert>{errText(analyze.error)}</Alert>}
      {drill.isError && <Alert>{errText(drill.error)}</Alert>}

      {analyze.data && (
        <Card>
          <h3 className="tf-card-title">Analysis</h3>
          <p className="tf-coach-analysis">{analyze.data.analysis}</p>
        </Card>
      )}
    </div>
  );
}
