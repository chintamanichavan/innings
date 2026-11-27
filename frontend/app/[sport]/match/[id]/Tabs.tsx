// The match centre's tabs. Each is its own address, so a tab can be shared and the back
// button works.

import Link from "next/link";

import { type Sport, link } from "@/lib/sport";

export const TABS = [
  ["summary", "Summary"],
  ["scorecard", "Scorecard"],
  ["commentary", "Commentary"],
  ["graphs", "Graphs"],
] as const;

export type Tab = (typeof TABS)[number][0];

export function tabOf(asked: string | undefined): Tab {
  return TABS.find(([tab]) => tab === asked)?.[0] ?? "summary";
}

export function Tabs({ sport, id, on }: { sport: Sport; id: string; on: Tab }) {
  return (
    <nav className="match-tabs" aria-label="Match sections">
      {TABS.map(([tab, name]) => (
        <Link
          key={tab}
          className={tab === on ? "on" : ""}
          href={link(sport, "match", id, tab === "summary" ? {} : { tab })}
          scroll={false}
          aria-current={tab === on ? "page" : undefined}
        >
          {name}
        </Link>
      ))}
    </nav>
  );
}
