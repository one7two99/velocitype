import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { lessonsApi, mcpApi } from "../api/endpoints";
import type { ApiKeyCreated } from "../api/types";
import { AiProvider } from "../components/AiProvider";
import { AiSettings } from "../components/AiSettings";
import { Button, Card, Field, Input, Spinner } from "../components/ui";
import { useNavHotkeys } from "../hooks/useNavHotkeys";
import { useSettings, type ThemePref } from "../stores/settingsStore";
import "./settings.css";

const THEMES: ThemePref[] = ["dark", "light", "system"];
const DURATIONS = [15, 30, 60, 120];
const WORD_COUNTS = [10, 25, 50, 100];

export function SettingsPage() {
  useNavHotkeys();
  const s = useSettings();
  const qc = useQueryClient();

  const layouts = useQuery({ queryKey: ["layouts"], queryFn: lessonsApi.layouts });
  const keys = useQuery({ queryKey: ["apikeys"], queryFn: mcpApi.listKeys });

  const [newKeyName, setNewKeyName] = useState("claude-web");
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);

  const createKey = useMutation({
    mutationFn: (name: string) => mcpApi.createKey(name),
    onSuccess: (data) => {
      setCreated(data);
      qc.invalidateQueries({ queryKey: ["apikeys"] });
    },
  });
  const revokeKey = useMutation({
    mutationFn: (id: string) => mcpApi.revokeKey(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apikeys"] }),
  });
  const resetProgression = useMutation({
    mutationFn: () => lessonsApi.resetProgression(s.layoutId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lessons", "unlock"] }),
  });

  return (
    <div className="tf-settings">
      <Card>
        <h3 className="tf-card-title">Appearance</h3>
        <Field label="Theme">
          <div className="tf-segmented">
            {THEMES.map((t) => (
              <button
                key={t}
                className={`tf-seg${s.theme === t ? " tf-seg--on" : ""}`}
                onClick={() => s.setTheme(t)}
              >
                {t}
              </button>
            ))}
          </div>
        </Field>
      </Card>

      <Card>
        <h3 className="tf-card-title">Training</h3>
        <Field label="Layout">
          <select
            className="tf-select"
            value={s.layoutId}
            onChange={(e) => s.setLayoutId(e.target.value)}
          >
            {layouts.data?.layouts.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Session goal">
          <div className="tf-segmented">
            <button
              className={`tf-seg${s.goal === "time" ? " tf-seg--on" : ""}`}
              onClick={() => s.setGoal("time")}
            >
              Timed
            </button>
            <button
              className={`tf-seg${s.goal === "words" ? " tf-seg--on" : ""}`}
              onClick={() => s.setGoal("words")}
            >
              Word count
            </button>
          </div>
        </Field>

        {s.goal === "time" ? (
          <Field label="Duration (seconds)">
            <div className="tf-segmented">
              {DURATIONS.map((d) => (
                <button
                  key={d}
                  className={`tf-seg${s.durationS === d ? " tf-seg--on" : ""}`}
                  onClick={() => s.setDurationS(d)}
                >
                  {d}s
                </button>
              ))}
            </div>
          </Field>
        ) : (
          <Field label="Words">
            <div className="tf-segmented">
              {WORD_COUNTS.map((w) => (
                <button
                  key={w}
                  className={`tf-seg${s.wordCount === w ? " tf-seg--on" : ""}`}
                  onClick={() => s.setWordCount(w)}
                >
                  {w}
                </button>
              ))}
            </div>
          </Field>
        )}

        <Field label={`Target speed — ${s.targetWpm} WPM`}>
          <div className="tf-range-row">
            <input
              type="range"
              className="tf-range"
              min={20}
              max={150}
              step={5}
              value={s.targetWpm}
              onChange={(e) => s.setTargetWpm(Number(e.target.value))}
            />
            <span className="tf-range-value mono">{s.targetWpm}</span>
          </div>
          <p className="tf-settings-note tf-range-hint">
            Keys are measured against this speed — slower keys get prioritised and
            "graduate" once they reach the target.
          </p>
        </Field>

        <Field label="Progressive key unlocking">
          <label className="tf-toggle-row">
            <input
              type="checkbox"
              checked={s.progressiveUnlock}
              onChange={(e) => s.setProgressiveUnlock(e.target.checked)}
            />
            Reveal keys one at a time as you master them (keybr-style)
          </label>
        </Field>

        {s.progressiveUnlock && (
          <>
            <Field label={`Unlock threshold — ${s.unlockThresholdPct}% of target`}>
              <div className="tf-range-row">
                <input
                  type="range"
                  className="tf-range"
                  min={50}
                  max={100}
                  step={5}
                  value={s.unlockThresholdPct}
                  onChange={(e) => s.setUnlockThresholdPct(Number(e.target.value))}
                />
                <span className="tf-range-value mono">{s.unlockThresholdPct}%</span>
              </div>
            </Field>
            <Field label={`Mastery window — ${s.unlockWindowSessions} session${s.unlockWindowSessions === 1 ? "" : "s"}`}>
              <div className="tf-range-row">
                <input
                  type="range"
                  className="tf-range"
                  min={1}
                  max={10}
                  step={1}
                  value={s.unlockWindowSessions}
                  onChange={(e) => s.setUnlockWindowSessions(Number(e.target.value))}
                />
                <span className="tf-range-value mono">{s.unlockWindowSessions}</span>
              </div>
              <p className="tf-settings-note tf-range-hint">
                A key unlocks the next once it reaches the threshold speed for this
                many sessions in a row. Lessons and AI drills only use unlocked keys.
              </p>
            </Field>
            <Field label="Reset progression">
              <Button
                variant="ghost"
                onClick={() => resetProgression.mutate()}
                disabled={resetProgression.isPending}
              >
                {resetProgression.isSuccess ? "Progression reset ✓" : "Reset to starting keys"}
              </Button>
              <p className="tf-settings-note">
                Restart from the initial keys for the current layout.
              </p>
            </Field>
          </>
        )}
      </Card>

      <AiProvider />

      <AiSettings />

      <Card>
        <h3 className="tf-card-title">MCP API Keys</h3>
        <p className="tf-settings-note">
          Long-lived keys for Claude coaching integration. The full key is shown
          once on creation — copy it now.
        </p>

        <div className="tf-key-create">
          <Input
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name"
          />
          <Button
            variant="primary"
            disabled={createKey.isPending || !newKeyName.trim()}
            onClick={() => createKey.mutate(newKeyName.trim())}
          >
            Generate
          </Button>
        </div>

        {created && (
          <div className="tf-key-reveal mono">
            <div className="tf-key-reveal-label">Copy your new key now:</div>
            <code>{created.api_key}</code>
          </div>
        )}

        {keys.isLoading ? (
          <Spinner />
        ) : keys.data && keys.data.keys.length > 0 ? (
          <table className="tf-keys">
            <thead>
              <tr>
                <th>Name</th>
                <th>Prefix</th>
                <th>Created</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {keys.data.keys.map((k) => (
                <tr key={k.id}>
                  <td>{k.name}</td>
                  <td className="mono">{k.prefix}…</td>
                  <td>{new Date(k.created_at).toLocaleDateString()}</td>
                  <td>{k.revoked_at ? "revoked" : "active"}</td>
                  <td>
                    {!k.revoked_at && (
                      <button
                        className="tf-btn tf-btn--danger tf-btn-sm"
                        onClick={() => revokeKey.mutate(k.id)}
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="tf-chart-empty">No API keys yet.</div>
        )}
      </Card>
    </div>
  );
}
