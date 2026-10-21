import { describe, expect, it } from "vitest";

import { ballsToOvers, keyFigures, num, oversToBalls, pct, signed } from "@/lib/format";

describe("numbers", () => {
  it("shows a dash for a missing value", () => {
    expect(num(null)).toBe("–");
    expect(signed(undefined)).toBe("–");
    expect(pct(null)).toBe("–");
  });

  it("groups thousands and keeps the asked decimals", () => {
    expect(num(5430745)).toBe("5,430,745");
    expect(num(1.4185, 3)).toBe("1.419");
  });

  it("signs with a true minus", () => {
    expect(signed(3.2, 1)).toBe("+3.2");
    expect(signed(-3.2, 1)).toBe("−3.2");
    expect(signed(0)).toBe("0");
  });

  it("never calls a live chance 0% or 100%", () => {
    expect(pct(0.004)).toBe("<1%");
    expect(pct(0.996)).toBe(">99%");
    expect(pct(0)).toBe("0%");
    expect(pct(1)).toBe("100%");
    expect(pct(0.62)).toBe("62%");
  });
});

describe("words", () => {
  it("marks the figures that carry a sentence, and loses no text", () => {
    const sentence = "West Indies had a 11% chance. Shai Hope: 162 off 143 balls.";
    const pieces = keyFigures(sentence);
    expect(pieces.filter((piece) => piece.key).map((piece) => piece.text)).toEqual([
      "11%",
      "162 off 143 balls",
    ]);
    expect(pieces.map((piece) => piece.text).join("")).toBe(sentence);
  });
});

describe("overs", () => {
  it("reads 14.3 as fourteen overs and three balls", () => {
    expect(oversToBalls("14.3")).toBe(87);
    expect(oversToBalls("20")).toBe(120);
    expect(oversToBalls("")).toBe(0);
  });

  it("writes balls back as overs", () => {
    expect(ballsToOvers(87)).toBe("14.3");
    expect(ballsToOvers(120)).toBe("20");
  });

  it("round-trips every ball of a T20 innings", () => {
    for (let balls = 0; balls <= 120; balls++) expect(oversToBalls(ballsToOvers(balls))).toBe(balls);
  });
});
