import { useState } from "react";

type Theme = "light" | "dark";

function currentTheme(): Theme {
  return document.documentElement.getAttribute("data-theme") === "dark"
    ? "dark"
    : "light";
}

function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;)\s*csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

/** Mirrors app/static/js/theme.js: flip data-theme, persist locally, PATCH preference. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(currentTheme);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    if (next === "dark")
      document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
    try {
      localStorage.setItem("theme", next);
    } catch {
      // storage unavailable — in-memory only
    }
    setTheme(next);
    void fetch("/api/v1/users/me/preferences", {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken(),
      },
      body: JSON.stringify({ theme: next }),
    }).catch(() => undefined);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={
        theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
      }
      className="rounded-md border border-border px-2 py-1 text-sm text-muted hover:text-text"
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
