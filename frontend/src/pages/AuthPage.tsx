import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { authApi } from "../api/endpoints";
import { Alert, Button, Field, Input } from "../components/ui";
import { useAuth, useInvalidateAuth } from "../hooks/useAuth";
import "./auth.css";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { user, isLoading } = useAuth();
  const invalidate = useInvalidateAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!isLoading && user) return <Navigate to="/" replace />;

  const isRegister = mode === "register";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (isRegister) {
        await authApi.register(username, email, password);
      } else {
        await authApi.login(username, password);
      }
      invalidate();
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        const first = err.problem?.errors?.[0];
        setError(first ? `${first.loc.at(-1)}: ${first.msg}` : err.message);
      } else {
        setError("Something went wrong.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="tf-auth">
      <form className="tf-auth-card" onSubmit={submit}>
        <div className="tf-auth-brand mono">
          Type<span>Forge</span>
        </div>
        <p className="tf-auth-sub">
          {isRegister ? "Create your account" : "Welcome back"}
        </p>

        {error && <Alert>{error}</Alert>}

        <Field label="Username" htmlFor="username">
          <Input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </Field>

        {isRegister && (
          <Field label="Email" htmlFor="email">
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </Field>
        )}

        <Field label="Password" htmlFor="password">
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isRegister ? "new-password" : "current-password"}
            required
          />
        </Field>
        {isRegister && (
          <p className="tf-auth-hint">Minimum 12 characters.</p>
        )}

        <Button variant="primary" type="submit" disabled={busy} className="tf-auth-submit">
          {busy ? "…" : isRegister ? "Create account" : "Log in"}
        </Button>

        <p className="tf-auth-switch">
          {isRegister ? (
            <>
              Already have an account? <Link to="/login">Log in</Link>
            </>
          ) : (
            <>
              New here? <Link to="/register">Create an account</Link>
            </>
          )}
        </p>
      </form>
    </div>
  );
}
