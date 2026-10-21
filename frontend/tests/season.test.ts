import { describe, expect, it } from "vitest";

import { type Tally, bigNumber, byTitle, diskSize } from "@/lib/season";

describe("big numbers in words", () => {
  it("names billions and millions, and writes smaller counts in full", () => {
    expect(bigNumber(1_768_867_000)).toBe("1.77 billion");
    expect(bigNumber(7_400_000)).toBe("7.4 million");
    expect(bigNumber(52_340)).toBe("52,340");
  });

  it("gives a file size in the unit that fits", () => {
    expect(diskSize(2_900_000_000)).toBe("2.9 GB");
    expect(diskSize(58_000_000)).toBe("58 MB");
  });
});

describe("ordering teams", () => {
  it("puts the likeliest champion first", () => {
    const tally = { teams: ["A", "B", "C"], title: [0.2, 0.5, 0.3] } as Tally;
    expect(byTitle(tally)).toEqual([1, 2, 0]);
  });
});
