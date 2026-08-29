import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { syncLogDetail, syncLogs } from "../../test/handlers";
import { server } from "../../test/setup";
import { SyncRow } from "./SyncRow";

describe("SyncRow (AC-009, AC-010)", () => {
  it("summarises a successful transfer and expands to its file list", async () => {
    const user = userEvent.setup();
    const ok = syncLogs.items[1];
    server.use(
      http.get("/api/v1/sync-logs/:id", () =>
        HttpResponse.json({
          ...syncLogDetail,
          ...ok,
          exit_code: 0,
          raw_content: "sent 1 bytes",
          file_list: [
            "Movies/Dune (2021)/Dune.mkv",
            "Movies/Heat (1995)/Heat.mkv",
          ],
          speedup_ratio: 1.02,
        }),
      ),
    );
    renderWithProviders(<SyncRow item={ok} />);
    const row = screen.getByTestId("sync-row");
    expect(row).toHaveAttribute("data-status", "ok");
    expect(row).toHaveTextContent("movies");
    expect(row).toHaveTextContent("4m 0s");
    expect(row).toHaveTextContent("5.8 GB");
    expect(row).toHaveTextContent("3 files");
    expect(screen.queryByTestId("sync-detail")).not.toBeInTheDocument();

    await user.click(within(row).getByRole("button"));
    const detail = await screen.findByTestId("sync-detail");
    expect(within(detail).getByTestId("file-list")).toHaveTextContent(
      "Dune.mkv",
    );
    expect(detail).toHaveTextContent("speedup 1.02×");
    expect(within(detail).queryByRole("presentation")).not.toBeInTheDocument();
  });

  it("shows exit code and raw output tail for a failed transfer", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SyncRow item={syncLogs.items[0]} defaultOpen />);
    expect(screen.getByTestId("sync-row")).toHaveAttribute(
      "data-status",
      "failed",
    );
    expect(screen.getByTestId("sync-row")).toHaveTextContent("exit 11");
    const detail = await screen.findByTestId("sync-detail");
    expect(detail).toHaveTextContent("No space left on device");
    // collapse again
    await user.click(screen.getByRole("button", { expanded: true }));
    expect(screen.queryByTestId("sync-detail")).not.toBeInTheDocument();
  });

  it("virtualises very long file lists", async () => {
    const many = Array.from(
      { length: 5000 },
      (_, i) => `Photos/2026/IMG_${i}.jpg`,
    );
    server.use(
      http.get("/api/v1/sync-logs/:id", () =>
        HttpResponse.json({ ...syncLogDetail, file_list: many }),
      ),
    );
    renderWithProviders(<SyncRow item={syncLogs.items[0]} defaultOpen />);
    const list = await screen.findByTestId("file-list");
    expect(list.querySelectorAll("div[title]").length).toBeLessThan(200);
    expect(screen.getByText("files (5,000)")).toBeInTheDocument();
  });
});
