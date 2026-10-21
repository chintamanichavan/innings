import { describe, expect, it } from "vitest";

import { link, queryString, sportOfSlug, teamHref } from "@/lib/sport";
import { flagOf, identity } from "@/lib/teams";

describe("addresses", () => {
  it("puts the front page at the sport's root", () => {
    expect(link("ck")).toBe("/cricket");
    expect(link("ck", "front")).toBe("/cricket");
  });

  it("escapes arguments and leaves empty options out", () => {
    expect(link("ck", "team", "Durban's Super Giants", { pool: "SA20", year: "" })).toBe(
      "/cricket/team/Durban's%20Super%20Giants?pool=SA20",
    );
    expect(queryString({ a: null, b: undefined, c: "" })).toBe("");
  });

  it("knows only cricket", () => {
    expect(sportOfSlug("cricket")).toBe("ck");
    expect(sportOfSlug("baseball")).toBeNull();
    expect(sportOfSlug("hockey")).toBeNull();
  });

  it("links a team within its league's pool", () => {
    expect(teamHref("ck", "IPL", "Mumbai Indians")).toBe("/cricket/team/Mumbai%20Indians?pool=IPL");
  });
});

describe("teams", () => {
  it("gives a nation its flag, and a women's side the same one", () => {
    expect(flagOf("India")).toBe("/flags/in.svg");
    expect(flagOf("India (W)")).toBe("/flags/in.svg");
    expect(flagOf("England")).toBe("/flags/gb-eng.svg");
  });

  it("gives clubs and flagless sides a roundel instead", () => {
    expect(flagOf("Mumbai Indians")).toBeNull();
    expect(flagOf("West Indies")).toBeNull();
    expect(identity("West Indies").code).toBe("WI");
  });

  it("always gives an unknown team the same colour and a short code", () => {
    expect(identity("Some New Club")).toEqual(identity("Some New Club"));
    expect(identity("Some New Club").code).toBe("SNC");
  });
});
