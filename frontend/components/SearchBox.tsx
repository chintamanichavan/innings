// A search box with a results menu under it. It finds players and teams as the reader types.

"use client";

import { type KeyboardEvent, type Ref, useRef, useState } from "react";

import { api } from "@/lib/api";
import { SPORTS, type Sport } from "@/lib/sport";
import type { Found, FoundPlayer, FoundTeam } from "@/lib/types";

import { Crest } from "./teams";

const WAIT_MS = 140; // pause after the last keystroke before searching
const MIN_LETTERS = 2;

interface SearchBoxProps {
  placeholder: string;
  onPick: (found: Found) => void;
  sport?: Sport; // only this sport's players
  playersOnly?: boolean;
  shown?: string; // text to show in the box, such as the chosen player's name
  inline?: boolean; // sits in a row of controls, not in the page header
  inputRef?: Ref<HTMLInputElement>;
  type?: "search" | "text";
}

interface FindAnswer {
  players: Omit<FoundPlayer, "kind">[];
  teams: Omit<FoundTeam, "kind">[];
}

export function SearchBox(props: SearchBoxProps) {
  const {
    placeholder,
    onPick,
    sport,
    playersOnly = false,
    shown,
    inline = false,
    inputRef,
    type,
  } = props;
  const [typed, setTyped] = useState<string | null>(null); // null until the reader types
  const [items, setItems] = useState<Found[] | null>(null); // null means the menu is closed
  const [active, setActive] = useState(-1);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const latest = useRef(0); // a slow answer must not replace a newer one

  const search = async (term: string) => {
    if (term.length < MIN_LETTERS) {
      setItems(null);
      return;
    }
    const asked = ++latest.current;
    const found = await api<FindAnswer>("find", { term });
    if (asked !== latest.current) return;
    const players = found.players.filter((player) => !sport || player.sport === sport);
    const teams = sport || playersOnly ? [] : found.teams;
    setItems([
      ...teams.map((team): Found => ({ kind: "team", ...team })),
      ...players.map((player): Found => ({ kind: "player", ...player })),
    ]);
    setActive(-1);
  };

  const choose = (index: number) => {
    const item = items?.[index];
    if (!item) return;
    setItems(null);
    setTyped(null);
    onPick(item);
  };

  const onKey = (event: KeyboardEvent) => {
    if (!items) return;
    if (event.key === "ArrowDown") setActive(Math.min(items.length - 1, active + 1));
    else if (event.key === "ArrowUp") setActive(Math.max(0, active - 1));
    else if (event.key === "Enter") choose(Math.max(0, active));
    else if (event.key === "Escape") setItems(null);
    else return;
    event.preventDefault();
  };

  return (
    <div className={inline ? "search inline" : "search"}>
      <input
        ref={inputRef}
        type={type}
        placeholder={placeholder}
        aria-label={placeholder}
        autoComplete="off"
        value={typed ?? shown ?? ""}
        onKeyDown={onKey}
        onChange={(event) => {
          const term = event.target.value;
          setTyped(term);
          clearTimeout(timer.current);
          timer.current = setTimeout(() => search(term.trim()), WAIT_MS);
        }}
        onBlur={() => setTimeout(() => setItems(null), 150)}
      />
      <ul className="menu" hidden={!items}>
        {items?.length === 0 && <li className="dim">No player or team by that name</li>}
        {items?.map((item, index) => (
          <li
            key={index}
            className={index === active ? "on" : ""}
            onMouseDown={(event) => {
              event.preventDefault();
              choose(index);
            }}
          >
            {item.kind === "team" ? (
              <>
                <span>
                  <Crest team={item.team} size="sm" /> {item.team}
                </span>
                <small>{item.pool}</small>
              </>
            ) : (
              <>
                <span>{item.name}</span>
                <small>{SPORTS[item.sport]}</small>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
