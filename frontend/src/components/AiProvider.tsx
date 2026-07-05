import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { coachApi } from "../api/endpoints";
import type { AiProvider as Provider } from "../api/types";
import { Alert, Button, Card, Input, Spinner } from "./ui";
import "./ai-provider.css";

// Curated Mistral cloud models offered in Settings (label → API model id).
// The "-latest" aliases currently resolve to exactly these versions.
const MISTRAL_MODELS: { value: string; label: string }[] = [
  { value: "mistral-small-latest", label: "Mistral Small 4" },
  { value: "mistral-medium-latest", label: "Mistral Medium 3.5" },
];

// Ensure the currently-selected value is always an option, even if listing failed.
function withCurrent(list: string[], current: string): string[] {
  return list.includes(current) ? list : [current, ...list];
}

// Same, for {value,label} option lists — preserves any previously-saved id.
function mistralOptionsFor(current: string): { value: string; label: string }[] {
  return MISTRAL_MODELS.some((m) => m.value === current)
    ? MISTRAL_MODELS
    : [{ value: current, label: current }, ...MISTRAL_MODELS];
}

export function AiProvider() {
  const qc = useQueryClient();
  const config = useQuery({ queryKey: ["coach", "config"], queryFn: coachApi.getConfig });

  const [provider, setProvider] = useState<Provider>("ollama");
  const [ollamaModel, setOllamaModel] = useState("");
  const [mistralModel, setMistralModel] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [keyDirty, setKeyDirty] = useState(false);
  const [pullName, setPullName] = useState("");
  const [pulling, setPulling] = useState<string | null>(null);

  useEffect(() => {
    if (!config.data) return;
    setProvider(config.data.provider);
    setOllamaModel(config.data.ollama_model);
    setMistralModel(config.data.mistral_model);
  }, [config.data]);

  const keySet = config.data?.mistral_key_set ?? false;

  // Only Ollama needs a dynamic model list (installed models). Mistral uses a
  // curated two-model dropdown.
  const models = useQuery({
    queryKey: ["coach", "models", "ollama"],
    queryFn: () => coachApi.listModels("ollama"),
    enabled: !!config.data && provider === "ollama",
  });

  const save = useMutation({
    mutationFn: () =>
      coachApi.saveConfig({
        provider,
        ollama_model: ollamaModel,
        mistral_model: mistralModel,
        ...(keyDirty ? { mistral_api_key: keyInput } : {}),
      }),
    onSuccess: (res) => {
      qc.setQueryData(["coach", "config"], res);
      qc.invalidateQueries({ queryKey: ["coach", "status"] });
      setKeyInput("");
      setKeyDirty(false);
    },
  });

  const clearKey = useMutation({
    mutationFn: () => coachApi.saveConfig({ mistral_api_key: "" }),
    onSuccess: (res) => {
      qc.setQueryData(["coach", "config"], res);
      qc.invalidateQueries({ queryKey: ["coach", "status"] });
    },
  });

  const pull = useMutation({
    mutationFn: (name: string) => coachApi.pullModel(name),
    onSuccess: (_res, name) => setPulling(name),
  });

  const pullQ = useQuery({
    queryKey: ["coach", "pull", pulling],
    queryFn: () => coachApi.pullStatus(pulling as string),
    enabled: !!pulling,
    refetchInterval: (q) => {
      const d = q.state.data;
      return d && (d.completed || d.error) ? false : 1500;
    },
  });

  useEffect(() => {
    if (pullQ.data?.completed) {
      qc.invalidateQueries({ queryKey: ["coach", "models"] });
    }
  }, [pullQ.data?.completed, qc]);

  if (config.isLoading || !config.data) {
    return (
      <Card>
        <h3 className="tf-card-title">AI Provider</h3>
        <Spinner />
      </Card>
    );
  }

  const ollamaOptions = withCurrent(models.data?.installed ?? [], ollamaModel);
  const mistralOptions = mistralOptionsFor(mistralModel);

  return (
    <Card>
      <h3 className="tf-card-title">AI Provider</h3>
      <p className="tf-settings-note">
        Choose where coaching (analysis &amp; drills) runs.
      </p>

      <div className="tf-segmented tf-provider-toggle">
        <button
          className={`tf-seg${provider === "ollama" ? " tf-seg--on" : ""}`}
          onClick={() => setProvider("ollama")}
        >
          Local · Ollama
        </button>
        <button
          className={`tf-seg${provider === "mistral" ? " tf-seg--on" : ""}`}
          onClick={() => setProvider("mistral")}
        >
          Mistral · Cloud (EU)
        </button>
      </div>

      {provider === "ollama" ? (
        <p className="tf-provider-privacy tf-provider-privacy--good">
          🔒 Runs entirely on your machine — not a single byte leaves your host.
        </p>
      ) : (
        <p className="tf-provider-privacy tf-provider-privacy--warn">
          ☁️ Your stats &amp; prompts are sent to Mistral's servers in the EU for
          processing. Use this only if you're comfortable with that.
        </p>
      )}

      {provider === "ollama" ? (
        <>
          <div className="tf-field">
            <label>Model</label>
            {models.data && !models.data.reachable && (
              <Alert>
                Ollama server not reachable. Is the <code>ollama</code> service running?
              </Alert>
            )}
            <select
              className="tf-select"
              value={ollamaModel}
              onChange={(e) => setOllamaModel(e.target.value)}
            >
              {ollamaOptions.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div className="tf-field">
            <label>Download a model</label>
            <div className="tf-pull-row">
              <Input
                value={pullName}
                onChange={(e) => setPullName(e.target.value)}
                placeholder="e.g. llama3.2:3b"
              />
              <Button
                onClick={() => pull.mutate(pullName.trim())}
                disabled={!pullName.trim() || (!!pulling && !pullQ.data?.completed && !pullQ.data?.error)}
              >
                Download
              </Button>
            </div>
            {pulling && pullQ.data && (
              <p className="tf-pull-status mono">
                {pullQ.data.error
                  ? `✗ ${pullQ.data.name}: ${pullQ.data.error}`
                  : pullQ.data.completed
                    ? `✓ ${pullQ.data.name} downloaded`
                    : `${pullQ.data.name}: ${pullQ.data.status}${
                        pullQ.data.percent != null ? ` (${pullQ.data.percent}%)` : ""
                      }`}
              </p>
            )}
            <p className="tf-prompt-hint">
              Downloads happen on the server and can take a while. Browse models at
              ollama.com/library.
            </p>
          </div>
        </>
      ) : (
        <>
          <div className="tf-field">
            <label>Mistral API key {keySet && <span className="tf-key-set">· key set ••••</span>}</label>
            <div className="tf-pull-row">
              <Input
                type="password"
                value={keyInput}
                onChange={(e) => {
                  setKeyInput(e.target.value);
                  setKeyDirty(true);
                }}
                placeholder={keySet ? "Enter a new key to replace" : "Paste your Mistral API key"}
                autoComplete="off"
              />
              {keySet && (
                <Button
                  variant="danger"
                  onClick={() => clearKey.mutate()}
                  disabled={clearKey.isPending}
                >
                  Clear
                </Button>
              )}
            </div>
            <p className="tf-prompt-hint">
              Stored encrypted on the server and never shown again. Get a key at
              console.mistral.ai.
            </p>
          </div>

          <div className="tf-field">
            <label>Model</label>
            <select
              className="tf-select"
              value={mistralModel}
              onChange={(e) => setMistralModel(e.target.value)}
            >
              {mistralOptions.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
        </>
      )}

      <div className="tf-ai-actions">
        <Button variant="primary" onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save provider"}
        </Button>
        {save.isSuccess && <span className="tf-ai-saved">Saved ✓</span>}
      </div>
    </Card>
  );
}
