import { describe, expect, it } from "vitest";
import { canManage, normalizeDate, terminalMissionStatuses } from "@/lib/api/types";

describe("API view-model helpers", () => {
  it("normalizes timezone-less backend dates", () => { expect(normalizeDate("2026-09-13T10:00:00")).toBe("2026-09-13T10:00:00Z"); expect(normalizeDate("2026-09-13T10:00:00+05:30")).toBe("2026-09-13T10:00:00+05:30"); });
  it("keeps role gates conservative", () => { expect(canManage("owner")).toBe(true); expect(canManage("manager")).toBe(true); expect(canManage("reviewer")).toBe(false); expect(canManage("viewer")).toBe(false); });
  it("recognizes all terminal mission states", () => { expect([...terminalMissionStatuses]).toEqual(["completed", "blocked", "rejected", "cancelled", "partially_complete", "failed"]); });
});
