import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { server } from "../test/setup";
import { ApiRequestError, buildQuery, fetchJson } from "./client";

describe("buildQuery", () => {
  it("drops empty values and encodes the rest", () => {
    expect(
      buildQuery({ a: 1, b: "x y", c: null, d: undefined, e: "", f: false }),
    ).toBe("?a=1&b=x+y&f=false");
    expect(buildQuery({})).toBe("");
  });
});

describe("fetchJson", () => {
  afterEach(() => vi.restoreAllMocks());

  it("returns parsed JSON on success", async () => {
    server.use(http.get("/api/v1/ping", () => HttpResponse.json({ ok: true })));
    await expect(fetchJson<{ ok: boolean }>("/ping")).resolves.toEqual({
      ok: true,
    });
  });

  it("throws ApiRequestError with the server message and code", async () => {
    server.use(
      http.get("/api/v1/broken", () =>
        HttpResponse.json(
          { message: "Monitor not found", error_code: "RESOURCE_NOT_FOUND" },
          { status: 404 },
        ),
      ),
    );
    const error = await fetchJson("/broken").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiRequestError);
    expect((error as ApiRequestError).status).toBe(404);
    expect((error as ApiRequestError).message).toBe("Monitor not found");
    expect((error as ApiRequestError).errorCode).toBe("RESOURCE_NOT_FOUND");
  });

  it("falls back to a generic message for non-JSON errors", async () => {
    server.use(
      http.get(
        "/api/v1/html",
        () => new HttpResponse("<h1>nope</h1>", { status: 502 }),
      ),
    );
    const error = (await fetchJson("/html").catch(
      (e: unknown) => e,
    )) as ApiRequestError;
    expect(error.message).toBe("Request failed (502)");
  });

  it("redirects to login with a return URL on 401", async () => {
    server.use(
      http.get("/api/v1/secret", () => HttpResponse.json({}, { status: 401 })),
    );
    const assign = vi.fn();
    vi.stubGlobal("location", {
      ...window.location,
      pathname: "/app/media",
      search: "?days=7",
      assign,
    });
    await expect(fetchJson("/secret")).rejects.toMatchObject({ status: 401 });
    expect(assign).toHaveBeenCalledWith(
      "/login?return_url=%2Fapp%2Fmedia%3Fdays%3D7",
    );
    vi.unstubAllGlobals();
  });

  it("returns undefined for 204", async () => {
    server.use(
      http.delete(
        "/api/v1/thing",
        () => new HttpResponse(null, { status: 204 }),
      ),
    );
    await expect(
      fetchJson("/thing", { method: "DELETE" }),
    ).resolves.toBeUndefined();
  });
});
