"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  ProfileResponse,
  ProfileUpdatePayload,
  RegisterPayload,
  getProfile,
  loginRequest,
  refreshRequest,
  registerRequest,
  updateProfileRequest,
} from "@/lib/api/endpoints/auth";

export type AuthUser = ProfileResponse;

type AuthContextValue = {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  updateProfile: (payload: ProfileUpdatePayload) => Promise<ProfileResponse>;
  logout: () => void;
  refresh: () => Promise<void>;
  reloadProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const ACCESS_TOKEN_KEY = "batumi_lunch_access_token";
const REFRESH_TOKEN_KEY = "batumi_lunch_refresh_token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedAccess = typeof window !== "undefined" ? localStorage.getItem(ACCESS_TOKEN_KEY) : null;
    const storedRefresh = typeof window !== "undefined" ? localStorage.getItem(REFRESH_TOKEN_KEY) : null;
    if (storedAccess && storedRefresh) {
      setAccessToken(storedAccess);
      setRefreshToken(storedRefresh);
      void fetchProfile(storedAccess, storedRefresh);
    } else {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const persistTokens = (access: string, refresh: string) => {
    setAccessToken(access);
    setRefreshToken(refresh);
    if (typeof window !== "undefined") {
      localStorage.setItem(ACCESS_TOKEN_KEY, access);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
    }
  };

  const clearTokens = () => {
    setAccessToken(null);
    setRefreshToken(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  };

  const fetchProfile = async (access: string, refresh: string) => {
    try {
      const profile = await getProfile(access);
      setUser(profile);
    } catch (error) {
      console.warn("Profile fetch failed, attempting refresh", error);
      try {
        const tokens = await refreshRequest(refresh);
        persistTokens(tokens.accessToken, tokens.refreshToken);
        const profile = await getProfile(tokens.accessToken);
        setUser(profile);
      } catch (refreshError) {
        console.error("Refresh failed", refreshError);
        clearTokens();
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const tokens = await loginRequest(email, password);
      persistTokens(tokens.accessToken, tokens.refreshToken);
      const profile = await getProfile(tokens.accessToken);
      setUser(profile);
      router.push("/order/new");
    } catch (error) {
      clearTokens();
      setUser(null);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  const register = useCallback(
    async (payload: RegisterPayload) => {
      setIsLoading(true);
      try {
        const tokens = await registerRequest(payload);
        persistTokens(tokens.accessToken, tokens.refreshToken);
        const profile = await getProfile(tokens.accessToken);
        setUser(profile);
        router.push("/order/new");
      } catch (error) {
        clearTokens();
        setUser(null);
        throw error;
      } finally {
        setIsLoading(false);
      }
  },
  [router]
  );

  const updateProfile = useCallback(
    async (payload: ProfileUpdatePayload) => {
      if (!accessToken) {
        throw new Error("Нет токена доступа");
      }
      setIsLoading(true);
      try {
        const profile = await updateProfileRequest(accessToken, payload);
        setUser(profile);
        return profile;
      } finally {
        setIsLoading(false);
      }
    },
    [accessToken]
  );

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    router.push("/login");
  }, [router]);

  const refresh = useCallback(async () => {
    if (!refreshToken) return;
    const tokens = await refreshRequest(refreshToken);
    persistTokens(tokens.accessToken, tokens.refreshToken);
    const profile = await getProfile(tokens.accessToken);
    setUser(profile);
  }, [refreshToken]);

  const reloadProfile = useCallback(async () => {
    if (!accessToken) return;
    try {
      const profile = await getProfile(accessToken);
      setUser(profile);
    } catch (error) {
      console.error("Profile reload failed", error);
    }
  }, [accessToken]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, accessToken, refreshToken, isLoading, login, register, updateProfile, logout, refresh, reloadProfile }),
    [user, accessToken, refreshToken, isLoading, login, register, updateProfile, logout, refresh, reloadProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
