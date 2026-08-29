import { screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import {
  syntheticStatusDisabled,
  syntheticStatusPassing,
} from "../../test/handlers";
import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { LivenessPill } from "./LivenessPill";

describe("LivenessPill (AC-001, AC-007)", () => {
  it("shows UP with uptime and last-check age", async () => {
    renderWithProviders(<LivenessPill />);
    expect(await screen.findByText("UP")).toBeInTheDocument();
    const pill = screen.getByTestId("liveness-pill");
    expect(pill).toHaveAttribute("data-status", "passing");
    expect(pill).toHaveTextContent("99.8%");
    expect(pill).toHaveTextContent(/checked .* ago/);
    expect(pill).toHaveAttribute("href", "/app/uptime");
  });

  it("shows DOWN when the latest check is failing", async () => {
    server.use(
      http.get("/api/v1/synthetic/status", () =>
        HttpResponse.json({
          ...syntheticStatusPassing,
          status: "failing",
          uptime_24h_pct: 91.2,
        }),
      ),
    );
    renderWithProviders(<LivenessPill />);
    expect(await screen.findByText("DOWN")).toBeInTheDocument();
    expect(screen.getByTestId("liveness-pill")).toHaveAttribute(
      "data-status",
      "failing",
    );
  });

  it("shows the disabled state with a link when synthetic monitoring is off", async () => {
    server.use(
      http.get("/api/v1/synthetic/status", () =>
        HttpResponse.json(syntheticStatusDisabled),
      ),
    );
    renderWithProviders(<LivenessPill />);
    expect(await screen.findByText("Synthetic check off")).toBeInTheDocument();
    expect(screen.getByTestId("liveness-pill")).toHaveAttribute(
      "data-status",
      "disabled",
    );
  });

  it("renders an unavailable state on API error", async () => {
    server.use(
      http.get("/api/v1/synthetic/status", () =>
        HttpResponse.json({ message: "boom" }, { status: 500 }),
      ),
    );
    renderWithProviders(<LivenessPill />);
    expect(await screen.findByText("status unavailable")).toBeInTheDocument();
  });
});
