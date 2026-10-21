import { describe, expect, it } from "vitest";

import { type LiveMatch, type Point, overs, runRate, status } from "@/lib/stream";

const MATCH = {
  match_id: "m",
  fmt: "T20",
  team1: "India",
  team2: "Australia",
  points: [],
} as unknown as LiveMatch;
const code = (team: string) => team.slice(0, 3).toUpperCase();

function point(more: Partial<Point>): Point {
  return {
    kind: "ball",
    match_id: "m",
    n: 1,
    innings: 1,
    bat_team: "India",
    score: 0,
    wickets: 0,
    balls_left: 120,
    target: null,
    wp1: 0.5,
    ...more,
  };
}

describe("scoreboard numbers", () => {
  it("writes overs and run rates the cricket way", () => {
    expect(overs(105)).toBe("17.3");
    expect(overs(120)).toBe("20");
    expect(runRate(180, 120)).toBe("9.00");
    expect(runRate(0, 0)).toBe("0.00");
  });

  it("says what the chase needs, then the result", () => {
    const chasing = point({
      innings: 2,
      bat_team: "Australia",
      score: 150,
      balls_left: 14,
      target: 181,
    });
    expect(status(MATCH, chasing, code)).toBe("AUS need 31 runs in 14 balls");
    const brk = point({ kind: "innings", innings: 2, bat_team: "Australia", target: 181 });
    expect(status(MATCH, brk, code)).toBe("Innings break. AUS need 181 to win");
    const end = point({ kind: "end", result: "India won by 10 runs" });
    expect(status(MATCH, end, code)).toBe("India won by 10 runs");
  });
});
