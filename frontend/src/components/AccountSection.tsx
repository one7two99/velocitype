import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { authApi } from "../api/endpoints";
import { useAuth, useClearAuth } from "../hooks/useAuth";
import { useCoachStore } from "../stores/coachStore";
import { Alert, Button, Card, Field, Input } from "./ui";
import "./account.css";

const MIN_PASSWORD = 12;

function errMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const first = err.problem?.errors?.[0];
    return first ? `${first.loc.at(-1)}: ${first.msg}` : err.message;
  }
  return "Something went wrong.";
}

export function AccountSection() {
  const { user } = useAuth();
  const clearAuth = useClearAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();

  // Change password
  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const changePassword = useMutation({
    mutationFn: () => authApi.changePassword(curPw, newPw),
    onSuccess: () => {
      setCurPw("");
      setNewPw("");
    },
  });

  // Change email
  const [email, setEmail] = useState("");
  const [emailPw, setEmailPw] = useState("");
  const changeEmail = useMutation({
    mutationFn: () => authApi.changeEmail(emailPw, email),
    onSuccess: () => {
      setEmail("");
      setEmailPw("");
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });

  // Reset all data (keep the account)
  const stopDrills = useCoachStore((s) => s.stopDrills);
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetPw, setResetPw] = useState("");
  const resetData = useMutation({
    mutationFn: () => authApi.resetData(resetPw),
    onSuccess: () => {
      setConfirmReset(false);
      setResetPw("");
      stopDrills();
      qc.invalidateQueries(); // refetch stats/coach/ngrams/sessions → fresh profile
    },
  });

  // Delete account
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deletePw, setDeletePw] = useState("");
  const deleteAccount = useMutation({
    mutationFn: () => authApi.deleteAccount(deletePw),
    onSuccess: () => {
      clearAuth();
      navigate("/login", { replace: true });
    },
  });

  return (
    <Card>
      <h3 className="tf-card-title">Account</h3>
      <p className="tf-account-current">
        Signed in as <span className="mono">{user?.username}</span> ·{" "}
        <span className="mono">{user?.email}</span>
      </p>

      {/* Change password */}
      <form
        className="tf-account-form"
        onSubmit={(e) => {
          e.preventDefault();
          changePassword.mutate();
        }}
      >
        <h4 className="tf-account-h">Change password</h4>
        {changePassword.isError && <Alert>{errMessage(changePassword.error)}</Alert>}
        {changePassword.isSuccess && (
          <div className="tf-account-ok">Password changed.</div>
        )}
        <Field label="Current password">
          <Input
            type="password"
            value={curPw}
            autoComplete="current-password"
            onChange={(e) => setCurPw(e.target.value)}
            required
          />
        </Field>
        <Field label={`New password (min ${MIN_PASSWORD})`}>
          <Input
            type="password"
            value={newPw}
            autoComplete="new-password"
            onChange={(e) => setNewPw(e.target.value)}
            required
          />
        </Field>
        <Button
          variant="primary"
          type="submit"
          disabled={
            changePassword.isPending || !curPw || newPw.length < MIN_PASSWORD
          }
        >
          Update password
        </Button>
      </form>

      {/* Change email */}
      <form
        className="tf-account-form"
        onSubmit={(e) => {
          e.preventDefault();
          changeEmail.mutate();
        }}
      >
        <h4 className="tf-account-h">Change email</h4>
        {changeEmail.isError && <Alert>{errMessage(changeEmail.error)}</Alert>}
        {changeEmail.isSuccess && <div className="tf-account-ok">Email updated.</div>}
        <Field label="New email">
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Field>
        <Field label="Confirm with password">
          <Input
            type="password"
            value={emailPw}
            autoComplete="current-password"
            onChange={(e) => setEmailPw(e.target.value)}
            required
          />
        </Field>
        <Button
          variant="primary"
          type="submit"
          disabled={changeEmail.isPending || !email || !emailPw}
        >
          Update email
        </Button>
      </form>

      {/* Reset all data */}
      <div className="tf-account-danger">
        <h4 className="tf-account-h">Delete all data</h4>
        <p className="tf-settings-note">
          Permanently deletes all your metrics (sessions, keystrokes, per-key and
          bigram stats) and your AI settings, including any stored Mistral API key.
          Your account and login are kept — you start fresh with empty stats. This
          cannot be undone.
        </p>
        {resetData.isError && <Alert>{errMessage(resetData.error)}</Alert>}
        {resetData.isSuccess && (
          <div className="tf-account-ok">All your data has been deleted.</div>
        )}
        {!confirmReset ? (
          <Button variant="danger" onClick={() => setConfirmReset(true)}>
            Delete all data…
          </Button>
        ) : (
          <form
            className="tf-account-form"
            onSubmit={(e) => {
              e.preventDefault();
              resetData.mutate();
            }}
          >
            <Field label="Confirm with password">
              <Input
                type="password"
                value={resetPw}
                autoComplete="current-password"
                onChange={(e) => setResetPw(e.target.value)}
                required
              />
            </Field>
            <div className="tf-account-danger-actions">
              <Button
                variant="danger"
                type="submit"
                disabled={resetData.isPending || !resetPw}
              >
                Delete all my data
              </Button>
              <Button
                variant="ghost"
                type="button"
                onClick={() => {
                  setConfirmReset(false);
                  setResetPw("");
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        )}
      </div>

      {/* Delete account */}
      <div className="tf-account-danger">
        <h4 className="tf-account-h">Delete account</h4>
        <p className="tf-settings-note">
          Permanently deletes your account and all sessions, stats, and API keys.
          This cannot be undone.
        </p>
        {deleteAccount.isError && <Alert>{errMessage(deleteAccount.error)}</Alert>}
        {!confirmDelete ? (
          <Button variant="danger" onClick={() => setConfirmDelete(true)}>
            Delete account…
          </Button>
        ) : (
          <form
            className="tf-account-form"
            onSubmit={(e) => {
              e.preventDefault();
              deleteAccount.mutate();
            }}
          >
            <Field label="Confirm with password">
              <Input
                type="password"
                value={deletePw}
                autoComplete="current-password"
                onChange={(e) => setDeletePw(e.target.value)}
                required
              />
            </Field>
            <div className="tf-account-danger-actions">
              <Button
                variant="danger"
                type="submit"
                disabled={deleteAccount.isPending || !deletePw}
              >
                Permanently delete
              </Button>
              <Button
                variant="ghost"
                type="button"
                onClick={() => {
                  setConfirmDelete(false);
                  setDeletePw("");
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        )}
      </div>
    </Card>
  );
}
