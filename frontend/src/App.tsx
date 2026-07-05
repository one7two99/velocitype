import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Spinner } from "./components/ui";
import { useAuth } from "./hooks/useAuth";
import { useSettingsSync } from "./hooks/useSettingsSync";
import { AnalysisPage } from "./pages/AnalysisPage";
import { AuthPage } from "./pages/AuthPage";
import { CoachPage } from "./pages/CoachPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HeatmapsPage } from "./pages/HeatmapsPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SettingsPage } from "./pages/SettingsPage";
import { TrainerPage } from "./pages/TrainerPage";
import { applyTheme, useSettings } from "./stores/settingsStore";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100vh" }}>
        <Spinner />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

export default function App() {
  const theme = useSettings((s) => s.theme);
  useEffect(() => applyTheme(theme), [theme]);
  useSettingsSync();

  return (
    <Routes>
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route
        path="/"
        element={
          <Protected>
            <TrainerPage />
          </Protected>
        }
      />
      <Route
        path="/dashboard"
        element={
          <Protected>
            <DashboardPage />
          </Protected>
        }
      />
      <Route
        path="/settings"
        element={
          <Protected>
            <SettingsPage />
          </Protected>
        }
      />
      <Route
        path="/profile"
        element={
          <Protected>
            <ProfilePage />
          </Protected>
        }
      />
      <Route
        path="/analysis"
        element={
          <Protected>
            <AnalysisPage />
          </Protected>
        }
      />
      <Route
        path="/heatmaps"
        element={
          <Protected>
            <HeatmapsPage />
          </Protected>
        }
      />
      <Route
        path="/coach"
        element={
          <Protected>
            <CoachPage />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
