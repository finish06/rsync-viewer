import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet } from "react-router";

import { usePreferences } from "../api/hooks";
import { currentUser, hasRole, type Role } from "./user";
import { LivenessPill } from "../features/liveness/LivenessPill";
import { ThemeToggle } from "./ThemeToggle";

// Navigation order is the spec's priority order (AC-023). Settings and admin
// are server-rendered pages behind the secondary menu.
export const NAV = [
  { to: "/app", label: "Overview", end: true },
  { to: "/app/transfers", label: "Transfers" },
  { to: "/app/trends", label: "Trends" },
  { to: "/app/media", label: "Media" },
  { to: "/app/uptime", label: "Uptime" },
];

const SECONDARY: { href: string; label: string; minRole?: Role }[] = [
  { href: "/notifications", label: "Notifications" },
  { href: "/settings", label: "Settings", minRole: "operator" },
  { href: "/admin/users", label: "Users", minRole: "admin" },
  { href: "/settings#changelog", label: "Changelog" },
];

/** Apply the server-stored theme once per load; the toggle keeps localStorage in sync afterwards. */
function useStoredTheme() {
  const prefs = usePreferences();
  useEffect(() => {
    const theme = prefs.data?.theme;
    if (!theme) return;
    if (theme === "dark")
      document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
    try {
      localStorage.setItem("theme", theme);
    } catch {
      // storage unavailable
    }
  }, [prefs.data?.theme]);
}

function navClass({ isActive }: { isActive: boolean }): string {
  return [
    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
    isActive ? "bg-bg-secondary text-text" : "text-muted hover:text-text",
  ].join(" ");
}

export function Shell() {
  useStoredTheme();
  return (
    <div className="min-h-screen bg-bg text-text">
      <header className="sticky top-0 z-20 border-b border-border bg-card/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-2">
          <NavLink to="/app" end className="text-base font-bold tracking-tight">
            ◉ Rsync Viewer
          </NavLink>
          <nav
            aria-label="Primary"
            className="hidden items-center gap-1 md:flex"
          >
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={navClass}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <LivenessPill />
            <ThemeToggle />
            <SecondaryMenu />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 pb-20 md:pb-6">
        <Outlet />
      </main>

      <nav
        aria-label="Primary (mobile)"
        className="fixed inset-x-0 bottom-0 z-20 flex justify-around border-t border-border bg-card py-1 md:hidden"
      >
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={navClass}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function SecondaryMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const user = currentUser();
  // Without injected context (e.g. the Vite dev server) show everything;
  // the server enforces the role on each destination anyway.
  const items = SECONDARY.filter(
    (item) => !user || !item.minRole || hasRole(user, item.minRole),
  );

  useEffect(() => {
    if (!open) return;
    function onClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Settings menu"
        onClick={() => setOpen((v) => !v)}
        className="rounded-md border border-border px-2 py-1 text-sm text-muted hover:text-text"
      >
        ⚙ ▾
      </button>
      {open && (
        <div
          role="menu"
          className="card absolute right-0 mt-1 w-44 overflow-hidden py-1 shadow-lg"
        >
          {user && (
            <div className="border-b border-border px-3 py-1.5 text-xs text-muted">
              {user.username} · {user.role}
            </div>
          )}
          {items.map((item) => (
            <a
              key={item.href}
              role="menuitem"
              href={item.href}
              className="block px-3 py-1.5 text-sm hover:bg-bg-secondary"
            >
              {item.label}
            </a>
          ))}
          <form method="post" action="/logout">
            <button
              type="submit"
              role="menuitem"
              className="block w-full px-3 py-1.5 text-left text-sm text-danger hover:bg-bg-secondary"
            >
              Log out
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
