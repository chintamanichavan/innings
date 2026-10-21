import { describe, expect, it } from "vitest";

import { type LiveMatch, type Point, type StreamRecord, inningsScore, isOver } from "@/lib/stream";
import { progress, withRecords } from "@/lib/stream";

const START: StreamRecord = {
  kind: "start",
  match_id: "m",
  fmt: "T20",
  competition: "IPL",
  team1: "India",
  team2: "Australia",
  venue: null,
  date: "2024-01-01",
};

function point(n: number, more: Partial<Point> = {}): Point {
  const base = { match_id: "m", n, innings: 1, bat_team: "India", score: n, wickets: 0 };
  return { kind: "ball", ...base, balls_left: 120 - n, target: null, wp1: 0.5, ...more };
}

describe("folding records into matches", () => {
  it("adds a match, then its balls in order", () => {
    const matches = withRecords([], [START, point(1), point(2)]);
    expect(matches).toHaveLength(1);
    expect(matches[0].points.map((each) => each.n)).toEqual([1, 2]);
    expect(matches[0].team1).toBe("India");
  });

  it("skips a record it has already seen", () => {
    const once = withRecords([], [START, point(1), point(2)]);
    const again = withRecords(once, [point(2), point(1), point(3)]);
    expect(again[0].points.map((each) => each.n)).toEqual([1, 2, 3]);
  });

  it("ignores a ball of a match it was never told about", () => {
    expect(withRecords([], [point(1)])).toEqual([]);
  });

  it("lets a new match take the place of a finished one", () => {
    const finished = withRecords([], [START, point(1), point(2, { kind: "end", wp1: 1 })]);
    expect(isOver(finished[0])).toBe(true);
    const next = withRecords(finished, [{ ...START, match_id: "second" }]);
    expect(next.map((match) => match.match_id)).toEqual(["second"]);
  });

  it("does not change the list it was given", () => {
    const before: LiveMatch[] = withRecords([], [START]);
    withRecords(before, [point(1)]);
    expect(before[0].points).toEqual([]);
  });
});

describe("placing a point on the chart", () => {
  it("gives each innings half the width", () => {
    expect(progress(point(1, { balls_left: 120 }), "T20")).toBe(0);
    expect(progress(point(1, { balls_left: 60 }), "T20")).toBe(0.25);
    expect(progress(point(1, { innings: 2, balls_left: 120 }), "T20")).toBe(0.5);
    expect(progress(point(1, { innings: 2, balls_left: 150 }), "ODI")).toBe(0.75);
    expect(progress(point(1, { kind: "end" }), "T20")).toBe(1);
  });
});

describe("an innings score", () => {
  it("is the latest ball of that innings", () => {
    const [match] = withRecords([], [START, point(1), point(2), point(3, { innings: 2, score: 0 })]);
    expect(inningsScore(match, 1)?.score).toBe(2);
    expect(inningsScore(match, 2)?.score).toBe(0);
    expect(inningsScore(withRecords([], [START])[0], 1)).toBeNull();
  });
});
