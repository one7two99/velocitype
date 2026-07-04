import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";
import { ApiError } from "../api/client";
import { authApi } from "../api/endpoints";
import type { User } from "../api/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  refetch: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    retry: (count, err) => {
      // Don't retry a legitimate 401 (just not logged in).
      if (err instanceof ApiError && err.status === 401) return false;
      return count < 2;
    },
    staleTime: 60_000,
  });

  return (
    <AuthContext.Provider
      value={{ user: data ?? null, isLoading, refetch: () => refetch() }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

/** Invalidate the cached user (after login/logout). */
export function useInvalidateAuth() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["me"] });
}
