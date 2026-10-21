import { describe, expect, it } from "vitest";

import { siteTeamName, timeAgo } from "@/lib/news";

const NOW = Date.parse("2026-10-09T12:00:00Z");

describe("how long ago", () => {
  it("counts minutes, then hours", () => {
    expect(timeAgo("2026-10-09T11:59:40Z", NOW)).toBe("just now");
    expect(timeAgo("2026-10-09T11:59:00Z", NOW)).toBe("1 minute ago");
    expect(timeAgo("2026-10-09T11:18:00Z", NOW)).toBe("42 minutes ago");
    expect(timeAgo("2026-10-09T09:00:00Z", NOW)).toBe("3 hours ago");
  });

  it("gives the date once a story is more than a day old", () => {
    expect(timeAgo("2026-10-05T12:00:00Z", NOW)).toBe("Oct 5");
  });

  it("says nothing without a date, and never goes negative", () => {
    expect(timeAgo(null, NOW)).toBe("");
    expect(timeAgo("2026-10-09T12:05:00Z", NOW)).toBe("just now");
  });
});

describe("team names from the live feed", () => {
  it("writes a women's side the way the rest of the site does", () => {
    expect(siteTeamName("Australia Women")).toBe("Australia (W)");
    expect(siteTeamName("India")).toBe("India");
  });
});
