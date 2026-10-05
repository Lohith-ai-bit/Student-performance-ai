"use client";

import type { AuthSession, Role, User } from "@/types";

const TOKEN_KEY = "spa_access_token";
const REFRESH_KEY = "spa_refresh_token";
const USER_KEY = "spa_user";
const SESSION_KEY = "spa_session";

export function saveSession(session: AuthSession) {
  localStorage.setItem(TOKEN_KEY, session.access_token);
  localStorage.setItem(REFRESH_KEY, session.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(session.user));
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  // lightweight cookies so Next.js middleware can route-guard without hitting the API
  document.cookie = `spa_token=${session.access_token}; path=/; max-age=${60 * 60 * 24 * 7}; samesite=lax`;
  document.cookie = `spa_role=${session.user.role}; path=/; max-age=${60 * 60 * 24 * 7}; samesite=lax`;
}

export function clearSession() {
  for (const key of [TOKEN_KEY, REFRESH_KEY, USER_KEY, SESSION_KEY]) localStorage.removeItem(key);
  document.cookie = "spa_token=; path=/; max-age=0";
  document.cookie = "spa_role=; path=/; max-age=0";
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function dashboardPathForRole(role: Role): string {
  switch (role) {
    case "STUDENT":
      return "/student/dashboard";
    case "FACULTY":
      return "/faculty/dashboard";
    case "ADMIN":
      return "/admin/dashboard";
  }
}
