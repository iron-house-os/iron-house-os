import { afterEach, describe, expect, it, vi } from "vitest";

import { customerQuotesApi } from "./customerQuotes";

describe("customerQuotesApi", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("preserves structured IHOS backend error messages", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ error: { message: "Reload before saving this quote." } }),
      { status: 409, headers: { "Content-Type": "application/json" } },
    )));

    await expect(customerQuotesApi.list()).rejects.toThrow("Reload before saving this quote.");
  });
});
