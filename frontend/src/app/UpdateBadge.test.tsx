import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { updateStatusNewer } from "../test/handlers";
import { renderWithProviders } from "../test/render";
import { server } from "../test/setup";
import { Shell } from "./Shell";

beforeEach(() => {
  window.__USER__ = { username: "cal", role: "admin" };
});
afterEach(() => {
  delete window.__USER__;
});

describe("update availability (AC-008)", () => {
  it("shows a gear badge and a release menu item when a newer version exists", async () => {
    server.use(
      http.get("/api/v1/version/updates", () =>
        HttpResponse.json(updateStatusNewer),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<Shell />);
    expect(await screen.findByTestId("update-badge")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Settings menu/ }));
    const item = screen.getByRole("menuitem", {
      name: /Update available.*v2\.18\.0/,
    });
    expect(item).toHaveAttribute(
      "href",
      "https://github.com/finish06/rsync-viewer/releases/tag/v2.18.0",
    );
  });

  it("shows neither badge nor menu item when up to date", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Shell />);
    await user.click(
      await screen.findByRole("button", { name: /Settings menu/ }),
    );
    within(screen.getByRole("menu")).getByRole("menuitem", {
      name: "Settings",
    });
    expect(screen.queryByTestId("update-badge")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("menuitem", { name: /Update available/ }),
    ).not.toBeInTheDocument();
  });
});
