// The bar at the foot of a phone screen.

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { type Sport, link } from "@/lib/sport";

import { TABS, tabOf } from "./sections";

const ICONS: Record<string, string> = {
  front: "M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z",
  scores: "M4 5h16v14H4zM12 5v14M4 12h16",
  forecasts: "M4 19V5M4 19h16M8 15l3.5-4 3 2.5L19 8",
  lab: "M9 3h6M10 3v6l-5 9a1.5 1.5 0 0 0 1.3 2.2h11.4A1.5 1.5 0 0 0 19 18l-5-9V3M7.5 14h9",
  sections: "M4 6h16M4 12h16M4 18h10",
};

export function TabBar({ sport }: { sport: Sport }) {
  const tab = tabOf(usePathname().split("/")[2] || "front");
  return (
    <nav className="tabbar" aria-label="Main">
      {TABS.map(([key, name]) => (
        <Link key={key} className={key === tab ? "on" : ""} href={link(sport, key)}>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d={ICONS[key]} />
          </svg>
          {name}
        </Link>
      ))}
    </nav>
  );
}
