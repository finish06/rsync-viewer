import { afterEach, describe, expect, it } from "vitest";

import { currentUser, hasRole } from "./user";

describe("injected user context", () => {
  afterEach(() => {
    delete window.__USER__;
  });

  it("reads the injected user and ranks roles", () => {
    expect(currentUser()).toBeNull();
    window.__USER__ = { username: "cal", role: "operator" };
    expect(currentUser()?.username).toBe("cal");
    expect(hasRole(currentUser(), "viewer")).toBe(true);
    expect(hasRole(currentUser(), "operator")).toBe(true);
    expect(hasRole(currentUser(), "admin")).toBe(false);
  });

  it("treats malformed context as anonymous", () => {
    window.__USER__ = { username: 123 as unknown as string, role: "admin" };
    expect(currentUser()).toBeNull();
    expect(hasRole(null, "viewer")).toBe(false);
  });
});
