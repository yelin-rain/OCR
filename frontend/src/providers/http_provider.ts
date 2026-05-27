import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import {
  clearTokens,
  emitAuthLogout,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "../utils/authToken";

/** 局域网访问时，用当前页面的 host 拼 API，避免同学电脑请求自己的 localhost */
function resolveApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE as string | undefined;
  if (fromEnv?.trim()) return fromEnv.trim().replace(/\/$/, "");

  const host = window.location.hostname;
  if (host && host !== "localhost" && host !== "127.0.0.1") {
    return `http://${host}:8000`;
  }
  return "http://localhost:8000";
}

const API_BASE = resolveApiBase();

export const httpClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) {
    clearTokens();
    emitAuthLogout();
    return null;
  }
  try {
    const res = await axios.post<{ access_token: string; refresh_token: string }>(
      `${API_BASE}/auth/refresh`,
      { refresh_token: refresh },
      { timeout: 15000 },
    );
    const { access_token, refresh_token } = res.data;
    setTokens(access_token, refresh_token);
    return access_token;
  } catch {
    clearTokens();
    emitAuthLogout();
    return null;
  }
}

export async function ensureValidAccessToken(): Promise<string | null> {
  const access = getAccessToken();
  const refresh = getRefreshToken();
  if (!access && !refresh) return null;
  if (access && !isAccessExpired(access)) return access;
  if (!refresh) {
    clearTokens();
    emitAuthLogout();
    return null;
  }
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

function isAccessExpired(token: string): boolean {
  try {
    const part = token.split(".")[1];
    if (!part) return true;
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json) as { exp?: number };
    if (!payload.exp) return true;
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

httpClient.interceptors.request.use(async (config) => {
  const url = config.url ?? "";
  if (url.includes("/auth/token") || url.includes("/auth/refresh") || url.includes("/auth/register")) {
    return config;
  }
  const token = await ensureValidAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (!original || error.response?.status !== 401) {
      return Promise.reject(error);
    }

    const url = original.url ?? "";
    if (
      url.includes("/auth/token") ||
      url.includes("/auth/refresh") ||
      original._retry
    ) {
      clearTokens();
      emitAuthLogout();
      return Promise.reject(error);
    }

    original._retry = true;
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }
    const newToken = await refreshPromise;
    if (!newToken) {
      return Promise.reject(error);
    }

    original.headers.Authorization = `Bearer ${newToken}`;
    return httpClient(original);
  },
);
