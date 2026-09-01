import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/render";
import { ExportPanel } from "./ExportPanel";

function open(props: Partial<Parameters<typeof ExportPanel>[0]> = {}) {
  const onDownload = vi.fn();
  renderWithProviders(
    <ExportPanel
      from="2026-08-01"
      to="2026-08-31"
      onClose={() => {}}
      onDownload={onDownload}
      {...props}
    />,
  );
  return onDownload;
}

describe("ExportPanel (AC-004..007)", () => {
  it("exports all sources without synthetic by default", async () => {
    const onDownload = open();
    const user = userEvent.setup();
    expect(await screen.findByLabelText("All sources")).toBeChecked();
    expect(screen.getByLabelText("Include synthetic checks")).not.toBeChecked();
    expect(screen.getByTestId("export-panel")).toHaveTextContent(
      /up to 10,000 rows/i,
    );
    await user.click(screen.getByRole("button", { name: "Download" }));
    const [url, filename] = onDownload.mock.calls[0];
    const params = new URL(url, "http://x").searchParams;
    expect(params.getAll("source")).toEqual([]);
    expect(params.get("synthetic")).toBe("hide");
    expect(params.get("start")).toBe("2026-08-01");
    expect(params.get("end")).toBe("2026-08-31");
    expect(filename).toMatch(/^rsync-export-\d{8}\.csv$/);
  });

  it("exports a chosen subset with synthetic included", async () => {
    const onDownload = open();
    const user = userEvent.setup();
    await user.click(await screen.findByLabelText("All sources")); // untick
    await user.click(screen.getByLabelText("movies"));
    await user.click(screen.getByLabelText("nas-backup"));
    await user.click(screen.getByLabelText("Include synthetic checks"));
    await user.selectOptions(screen.getByLabelText("Format"), "json");
    await user.click(screen.getByRole("button", { name: "Download" }));
    const [url, filename] = onDownload.mock.calls[0];
    const params = new URL(url, "http://x").searchParams;
    expect(params.getAll("source")).toEqual(["movies", "nas-backup"]);
    expect(params.get("synthetic")).toBe("show");
    expect(params.get("format")).toBe("json");
    expect(filename).toMatch(/\.json$/);
  });

  it("refuses to export with nothing selected (AC / TC-003)", async () => {
    open();
    const user = userEvent.setup();
    await user.click(await screen.findByLabelText("All sources"));
    const button = screen.getByRole("button", { name: "Download" });
    expect(button).toBeDisabled();
    expect(screen.getByTestId("export-panel")).toHaveTextContent(
      /select at least one source/i,
    );
  });

  it("lists the known sources from the API", async () => {
    open();
    const user = userEvent.setup();
    // the checkbox list appears once "All sources" is unticked
    await user.click(await screen.findByLabelText("All sources"));
    const list = await screen.findByTestId("export-sources");
    for (const name of ["movies", "nas-backup", "photos"]) {
      expect(within(list).getByLabelText(name)).toBeInTheDocument();
    }
  });
});
