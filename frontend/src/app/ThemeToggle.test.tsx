import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { server } from "../test/setup";
import { ThemeToggle } from "./ThemeToggle";

describe("ThemeToggle", () => {
  let patched: { theme?: string } | null = null;
  let csrfHeader: string | null = null;

  beforeEach(() => {
    patched = null;
    csrfHeader = null;
    document.documentElement.removeAttribute("data-theme");
    localStorage.clear();
    document.cookie = "csrf_token=abc123";
    server.use(
      http.patch("/api/v1/users/me/preferences", async ({ request }) => {
        patched = (await request.json()) as { theme?: string };
        csrfHeader = request.headers.get("X-CSRF-Token");
        return HttpResponse.json({ theme: patched.theme });
      }),
    );
  });

  afterEach(() => {
    document.documentElement.removeAttribute("data-theme");
  });

  it("switches to dark, persists locally, and PATCHes the preference with CSRF", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(
      screen.getByRole("button", { name: "Switch to dark theme" }),
    );
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(localStorage.getItem("theme")).toBe("dark");
    await screen.findByRole("button", { name: "Switch to light theme" });
    await new Promise((r) => setTimeout(r, 20));
    expect(patched).toEqual({ theme: "dark" });
    expect(csrfHeader).toBe("abc123");
  });

  it("switches back to light", async () => {
    document.documentElement.setAttribute("data-theme", "dark");
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(
      screen.getByRole("button", { name: "Switch to light theme" }),
    );
    expect(document.documentElement).not.toHaveAttribute("data-theme");
    expect(localStorage.getItem("theme")).toBe("light");
  });
});
