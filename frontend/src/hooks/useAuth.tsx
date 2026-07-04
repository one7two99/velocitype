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

// Resolve the current user, treating a 401 as "logged out" (null) rather than an
// error. This matters because React Query retains the last successful `data` on
// error — without this, a 401 after logout would leave the stale user in place.
async function fetchMe(): Promise<User | null> {
  try {
    return await authApi.me();
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
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

/** Refetch the cached user (after login/register). */
export function useInvalidateAuth() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["me"] });
}

/** Immediately clear the cached user (after logout / account deletion). */
export function useClearAuth() {
  const qc = useQueryClient();
  return () => qc.setQueryData(["me"], null);
}
