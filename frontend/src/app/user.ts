// The FastAPI shell route injects the signed-in user before first paint
// (app/routes/spa.py) so the menu is role-aware without a round trip.

export type Role = "admin" | "operator" | "viewer";

export interface CurrentUser {
  username: string;
  role: Role;
  theme?: "light" | "dark" | null;
}

declare global {
  interface Window {
    __USER__?: CurrentUser;
    __USER_THEME__?: string;
    __APP_VERSION__?: string;
  }
}

const RANK: Record<Role, number> = { viewer: 0, operator: 1, admin: 2 };

export function currentUser(): CurrentUser | null {
  const user = typeof window !== "undefined" ? window.__USER__ : undefined;
  if (!user || typeof user.username !== "string") return null;
  return user;
}

export function hasRole(user: CurrentUser | null, minimum: Role): boolean {
  if (!user || !(user.role in RANK)) return false;
  return RANK[user.role] >= RANK[minimum];
}

/** Server-injected build version; null on an old cached shell or dev proxy. */
export function appVersion(): string | null {
  const version =
    typeof window !== "undefined" ? window.__APP_VERSION__ : undefined;
  return typeof version === "string" && version.length > 0 ? version : null;
}
