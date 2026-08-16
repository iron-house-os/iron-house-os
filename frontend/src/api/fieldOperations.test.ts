import { afterEach, describe, expect, it, vi } from "vitest";

import { fieldOperationsApi, formatApiErrorDetail } from "./fieldOperations";

describe("field operations API errors", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("formats FastAPI validation issues without object coercion", () => {
    expect(formatApiErrorDetail([
      {
        type: "literal_error",
        loc: ["body", "record_type"],
        msg: "Input should be a permitted record type",
      },
      {
        type: "missing",
        loc: ["body", "title"],
        msg: "Field required",
      },
    ])).toBe("record_type: Input should be a permitted record type; title: Field required");
  });

  it("surfaces structured validation errors from a PO request", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: [{ loc: ["body", "record_type"], msg: "Input should be a permitted record type" }],
    }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(fieldOperationsApi.createRecord({
      record_type: "purchase_order_request",
    })).rejects.toThrow("record_type: Input should be a permitted record type");
  });

  it("formats structured message and blocker responses", () => {
    expect(formatApiErrorDetail({
      message: "Receipt approval is blocked.",
      blockers: ["Select a project.", "Confirm the vendor."],
    })).toBe("Receipt approval is blocked. Select a project. Confirm the vendor.");
  });
});
