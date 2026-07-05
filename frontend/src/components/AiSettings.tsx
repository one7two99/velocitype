import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { coachApi } from "../api/endpoints";
import type { PromptCustom, PromptKey, PromptSet } from "../api/types";
import { Button, Card, Spinner } from "./ui";
import "./ai-settings.css";

const FIELDS: { key: PromptKey; label: string; hint?: string; rows: number }[] = [
  { key: "analysis_system", label: "Analysis · system prompt", rows: 3 },
  {
    key: "analysis_user",
    label: "Analysis · instruction",
    hint: "Use {{data}} where the trainee stats (JSON) should be inserted.",
    rows: 7,
  },
  { key: "drill_system", label: "Drill · system prompt", rows: 3 },
  {
    key: "drill_user",
    label: "Drill · instruction",
    hint: "Use {{focus}} where the weak keys should be inserted.",
    rows: 7,
  },
];

export function AiSettings() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["coach", "prompts"],
    queryFn: coachApi.getPrompts,
  });
  const [fields, setFields] = useState<PromptSet | null>(null);

  useEffect(() => {
    if (!data) return;
    setFields({
      analysis_system: data.custom.analysis_system ?? data.defaults.analysis_system,
      analysis_user: data.custom.analysis_user ?? data.defaults.analysis_user,
      drill_system: data.custom.drill_system ?? data.defaults.drill_system,
      drill_user: data.custom.drill_user ?? data.defaults.drill_user,
    });
  }, [data]);

  const save = useMutation({
    mutationFn: (custom: PromptCustom) => coachApi.savePrompts(custom),
    onSuccess: (res) => qc.setQueryData(["coach", "prompts"], res),
  });

  if (isLoading || !data || !fields) {
    return (
      <Card>
        <h3 className="tf-card-title">AI Settings</h3>
        <Spinner />
      </Card>
    );
  }

  const d = data.defaults;
  // A field equal to the default is sent as null so it tracks future default changes.
  const toCustom = (f: PromptSet): PromptCustom => ({
    analysis_system: f.analysis_system === d.analysis_system ? null : f.analysis_system,
    analysis_user: f.analysis_user === d.analysis_user ? null : f.analysis_user,
    drill_system: f.drill_system === d.drill_system ? null : f.drill_system,
    drill_user: f.drill_user === d.drill_user ? null : f.drill_user,
  });

  const isCustom = (k: PromptKey) => fields[k] !== d[k];

  return (
    <Card>
      <h3 className="tf-card-title">AI Settings</h3>
      <p className="tf-settings-note">
        The prompts sent to the local AI coach. Edit to fine-tune tone and focus;
        the app automatically injects your stats. Leave a field at its default (or
        use “Reset to defaults”) to follow the built-in prompt.
      </p>

      {FIELDS.map((f) => (
        <div key={f.key} className="tf-field">
          <label>
            {f.label}
            {isCustom(f.key) && <span className="tf-prompt-custom"> · customized</span>}
          </label>
          <textarea
            className="tf-prompt-area mono"
            rows={f.rows}
            value={fields[f.key]}
            onChange={(e) => setFields({ ...fields, [f.key]: e.target.value })}
          />
          {f.hint && <p className="tf-prompt-hint">{f.hint}</p>}
        </div>
      ))}

      <div className="tf-ai-actions">
        <Button
          variant="primary"
          disabled={save.isPending}
          onClick={() => save.mutate(toCustom(fields))}
        >
          {save.isPending ? "Saving…" : "Save prompts"}
        </Button>
        <Button
          variant="ghost"
          disabled={save.isPending}
          onClick={() => {
            setFields({ ...d });
            save.mutate({
              analysis_system: null,
              analysis_user: null,
              drill_system: null,
              drill_user: null,
            });
          }}
        >
          Reset to defaults
        </Button>
        {save.isSuccess && <span className="tf-ai-saved">Saved ✓</span>}
      </div>
    </Card>
  );
}
