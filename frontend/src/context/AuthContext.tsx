import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { httpClient } from "../providers/http_provider";
import { ensureValidAccessToken } from "../providers/http_provider";
import {
  AUTH_LOGOUT_EVENT,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isTokenExpiringSoon,
  setTokens,
} from "../utils/authToken";

interface User {
  id: number;
  email: string;
  username: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const REFRESH_AHEAD_MS = 5 * 60 * 1000;

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshTimerRef = useRef<number | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current !== null) {
      window.clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const fetchUser = useCallback(async () => {
    const response = await httpClient.get("/auth/me");
    setUser(response.data);
  }, []);

  const scheduleProactiveRefresh = useCallback(() => {
    clearRefreshTimer();
    const access = getAccessToken();
    if (!access) return;

    const expMs = (() => {
      try {
        const part = access.split(".")[1];
        const payload = JSON.parse(
          atob(part.replace(/-/g, "+").replace(/_/g, "/")),
        ) as { exp?: number };
        return payload.exp ? payload.exp * 1000 : null;
      } catch {
        return null;
      }
    })();

    if (!expMs) return;

    const delay = Math.max(10_000, expMs - Date.now() - REFRESH_AHEAD_MS);
    refreshTimerRef.current = window.setTimeout(async () => {
      const token = await ensureValidAccessToken();
      if (token) {
        scheduleProactiveRefresh();
      }
    }, delay);
  }, [clearRefreshTimer]);

  const login = async (accessToken: string, refreshToken: string) => {
    setTokens(accessToken, refreshToken);
    try {
      await fetchUser();
      scheduleProactiveRefresh();
    } catch (error) {
      console.error("Failed to fetch user profile", error);
    }
  };

  const logout = useCallback(() => {
    clearRefreshTimer();
    clearTokens();
    setUser(null);
  }, [clearRefreshTimer]);

  const refreshUser = async () => {
    await fetchUser();
  };

  useEffect(() => {
    const init = async () => {
      const access = getAccessToken();
      const refresh = getRefreshToken();
      if (!access && !refresh) {
        setLoading(false);
        return;
      }
      try {
        if (access && isTokenExpiringSoon(access) && refresh) {
          await ensureValidAccessToken();
        }
        await fetchUser();
        scheduleProactiveRefresh();
      } catch {
        clearTokens();
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    void init();

    const onLogout = () => {
      clearRefreshTimer();
      setUser(null);
    };
    const onFocus = () => {
      const token = getAccessToken();
      if (token && isTokenExpiringSoon(token)) {
        void ensureValidAccessToken().then((t) => {
          if (t) scheduleProactiveRefresh();
        });
      }
    };

    window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);
    window.addEventListener("focus", onFocus);
    return () => {
      clearRefreshTimer();
      window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
      window.removeEventListener("focus", onFocus);
    };
  }, [clearRefreshTimer, fetchUser, scheduleProactiveRefresh]);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
