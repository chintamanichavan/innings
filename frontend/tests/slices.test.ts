import { describe, expect, it } from "vitest";

import { needsStyles, roleOf, sliceOf, splitsFor } from "../lib/slices";

describe("slices", () => {
  it("keeps only slice fields from a page's query", () => {
    expect(sliceOf({ batter: "x", phase: "death", tab: "y", q: "z" })).toEqual({
      batter: "x",
      phase: "death",
    });
  });

  it("shows the bowler's numbers only when a bowler is named alone", () => {
    expect(roleOf({ bowler: "b" })).toBe("bowl");
    expect(roleOf({ batter: "a", bowler: "b" })).toBe("bat");
    expect(roleOf({})).toBe("bat");
    expect(roleOf({ bowler: "b", role: "bat" })).toBe("bat");
  });

  it("offers the other side's style as a split", () => {
    const keys = (role: "bat" | "bowl") => splitsFor(role).map(([key]) => key);
    expect(keys("bat")).toContain("type");
    expect(keys("bat")).not.toContain("hand");
    expect(keys("bowl")).toContain("hand");
    expect(keys("bowl")).not.toContain("type");
  });

  it("knows when a table leans on styles we only partly know", () => {
    expect(needsStyles({ by: "type" })).toBe("type");
    expect(needsStyles({ family: "spin" })).toBe("family");
    expect(needsStyles({ hand: "L" })).toBe("hand");
    expect(needsStyles({ by: "year" })).toBeNull();
  });
});
