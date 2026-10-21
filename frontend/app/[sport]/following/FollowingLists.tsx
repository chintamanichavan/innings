// The Following page's lists. Teams and players live on this device, so these run in the browser.

"use client";

import Link from "next/link";

import { StoryCard } from "@/components/matches";
import { Face } from "@/components/teams";
import { openTeamSheet } from "@/components/frame/TeamSheet";
import { SPORTS, link } from "@/lib/sport";
import { type FollowedPlayer, useStored } from "@/lib/store";

import { useLatest } from "../useLatest";

export function TeamCards() {
  const latest = useLatest();
  if (!latest) return null;
  if (!latest.length) return <p className="empty">You are not following any teams yet.</p>;
  return (
    <div className="cols3">
      {latest.map((item) => (
        <StoryCard key={item.team} match={item.match} label={item.team} />
      ))}
    </div>
  );
}

export function EditTeamsButton() {
  return (
    <button className="btn alt" onClick={openTeamSheet}>
      Choose your game and teams
    </button>
  );
}

export function PlayerRows() {
  const players = useStored<FollowedPlayer[]>("follows", []);
  if (!players.length) return <p className="empty">Open any player and press Follow.</p>;
  return (
    <div className="rows narrow">
      {players.map((player) => (
        <Link
          key={`${player.sport}-${player.id}`}
          className="rowlink"
          href={link(player.sport, "player", player.id)}
        >
          <Face name={player.name} />
          <span>
            <b>{player.name}</b>
            <small>{SPORTS[player.sport]}</small>
          </span>
          <span aria-hidden="true">→</span>
        </Link>
      ))}
    </div>
  );
}
