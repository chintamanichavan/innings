// The top of every page: the name, search, the theme button and the menu.

"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { SearchBox } from "@/components/SearchBox";
import { type Sport, link } from "@/lib/sport";
import { store } from "@/lib/store";
import type { Found } from "@/lib/types";

import { SECTIONS, sectionOf } from "./sections";

function toggleTheme() {
  const root = document.documentElement;
  const chosen = root.dataset.theme;
  const dark = chosen ? chosen === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  const next = dark ? "light" : "dark";
  root.dataset.theme = next;
  store.set("theme", next);
}

export function Mast({ sport }: { sport: Sport }) {
  const router = useRouter();
  const page = usePathname().split("/")[2] || "front";
  const section = sectionOf(page);
  const search = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName ?? "");
      if (event.key !== "/" || typing) return;
      event.preventDefault();
      search.current?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const open = (found: Found) => {
    search.current?.blur();
    if (found.kind === "team") router.push(link(found.sport, "team", found.team, { pool: found.pool }));
    else router.push(link(found.sport, "player", found.player_id));
  };

  return (
    <header className="mast">
      <div className="mast-top">
        <Link className="wordmark" href={link(sport)} aria-label="Innings, front page">
          Innings
        </Link>
        <SearchBox
          placeholder="Search players and teams"
          onPick={open}
          inputRef={search}
          type="search"
        />
        <button className="ghost" aria-label="Switch between light and dark" onClick={toggleTheme}>
          <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
            <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="M10 3a7 7 0 0 1 0 14z" fill="currentColor" />
          </svg>
        </button>
      </div>
      <nav className="sections" aria-label="Sections">
        {SECTIONS.map(([key, name]) => (
          <Link
            key={key}
            className={key === section ? "on" : ""}
            href={link(sport, key)}
            aria-current={key === section ? "page" : undefined}
          >
            {name}
          </Link>
        ))}
      </nav>
    </header>
  );
}
