import { describe, expect, it } from "vitest";

import { SYMBOLS, symbolOf } from "@/lib/badges";

describe("club badges", () => {
  it("takes a club's symbol from its name", () => {
    expect(symbolOf("Chennai Super Kings")).toBe("crown");
    expect(symbolOf("Sunrisers Hyderabad")).toBe("sun");
    expect(symbolOf("Kolkata Knight Riders")).toBe("sword");
    expect(symbolOf("Brisbane Heat")).toBe("flame");
    expect(symbolOf("Sydney Thunder")).toBe("bolt");
    expect(symbolOf("Durban's Super Giants")).toBe("mountain");
    expect(symbolOf("MI Cape Town")).toBe("wave");
  });

  it("matches whole words only, and gives none when no word fits", () => {
    expect(symbolOf("Victoria")).toBeNull();
    expect(symbolOf("Kingston")).toBeNull();
    expect(symbolOf("West Indies")).toBeNull();
  });

  it("gives every IPL, BBL, PSL, CPL and SA20 club a symbol", () => {
    const clubs = [
      "Chennai Super Kings",
      "Mumbai Indians",
      "Royal Challengers Bengaluru",
      "Kolkata Knight Riders",
      "Sunrisers Hyderabad",
      "Delhi Capitals",
      "Punjab Kings",
      "Rajasthan Royals",
      "Gujarat Titans",
      "Lucknow Super Giants",
      "Adelaide Strikers",
      "Brisbane Heat",
      "Hobart Hurricanes",
      "Melbourne Renegades",
      "Melbourne Stars",
      "Perth Scorchers",
      "Sydney Sixers",
      "Sydney Thunder",
      "Islamabad United",
      "Karachi Kings",
      "Lahore Qalandars",
      "Multan Sultans",
      "Peshawar Zalmi",
      "Quetta Gladiators",
      "Barbados Royals",
      "Guyana Amazon Warriors",
      "Jamaica Tallawahs",
      "St Kitts and Nevis Patriots",
      "St Lucia Kings",
      "Trinbago Knight Riders",
      "Antigua and Barbuda Falcons",
      "Durban's Super Giants",
      "Joburg Super Kings",
      "MI Cape Town",
      "Paarl Royals",
      "Pretoria Capitals",
      "Sunrisers Eastern Cape",
    ];
    for (const club of clubs) expect(symbolOf(club), club).not.toBeNull();
  });

  it("draws every symbol as a path", () => {
    for (const symbol of Object.values(SYMBOLS)) expect(symbol.path).toMatch(/^M/);
  });
});
