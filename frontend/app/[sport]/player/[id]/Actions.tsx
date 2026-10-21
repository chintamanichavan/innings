// Follow, share and compare, which sit under a player's name. Following lives on the device.

"use client";

import Link from "next/link";

import { FollowButton, ShareButton } from "@/components/controls";
import { type Sport, link } from "@/lib/sport";
import { followedPlayers, togglePlayer } from "@/lib/store";

export function Actions({ sport, id, name }: { sport: Sport; id: string; name: string }) {
  const isFollowing = () =>
    followedPlayers().some((player) => player.sport === sport && player.id === id);
  return (
    <p className="row spaced">
      <FollowButton isFollowing={isFollowing} toggle={() => togglePlayer({ sport, id, name })} />
      <ShareButton title={name} />
      <Link className="btn alt sm" href={link(sport, "compare", "", { a: id })}>
        Compare
      </Link>
    </p>
  );
}
