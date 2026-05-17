const ACCESS_KEY = "token";
const REFRESH_KEY = "refresh_token";

export type TokenPair = {
  access_token: string;
  refresh_token: string;
};

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/** 解析 JWT 过期时间（毫秒时间戳） */
export function getTokenExpiryMs(token: string): number | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json) as { exp?: number };
    return payload.exp ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/** 是否在 thresholdMs 内即将过期 */
export function isTokenExpiringSoon(token: string, thresholdMs = 5 * 60 * 1000): boolean {
  const exp = getTokenExpiryMs(token);
  if (!exp) return true;
  return exp - Date.now() <= thresholdMs;
}

export function isTokenExpired(token: string): boolean {
  const exp = getTokenExpiryMs(token);
  if (!exp) return true;
  return Date.now() >= exp;
}

export const AUTH_LOGOUT_EVENT = "auth:logout";

export function emitAuthLogout() {
  window.dispatchEvent(new CustomEvent(AUTH_LOGOUT_EVENT));
}
