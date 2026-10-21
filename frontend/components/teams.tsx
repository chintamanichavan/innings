// Teams and players as they appear in lists: a flag, badge or roundel, and a name.

import Link from "next/link";
import type { ReactNode } from "react";

import { type Sport, link, teamHref } from "@/lib/sport";
import { SYMBOLS, symbolOf } from "@/lib/badges";
import { flagOf, identity } from "@/lib/teams";

export type Size = "" | "sm" | "lg" | "xl";

// The shield every club badge shares, in a 40 by 44 box.
const SHIELD = "M20 2 36 7v15c0 10-7 16.5-16 20C11 38.5 4 32 4 22V7z";
const SMALL_SIZES: Size[] = ["", "sm"]; // too small for letters: the symbol alone must do

/** A club's badge: our shield in the club's colour, with its symbol and short code. */
function Badge({ team, size }: { team: string; size: Size }) {
  const { color, code, dark } = identity(team);
  const ink = dark ? "#171717" : "#fff";
  const symbolName = symbolOf(team);
  const symbol = symbolName ? SYMBOLS[symbolName] : null;
  const lettered = !symbol || !SMALL_SIZES.includes(size);
  // With letters below it the symbol sits high and small; alone it fills the shield.
  const place = lettered ? "translate(11.6 6.5) scale(0.7)" : "translate(8 9) scale(1)";
  return (
    <svg className={`crest badge ${size}`} viewBox="0 0 40 44" aria-hidden="true">
      <path d={SHIELD} fill={color} />
      <path
        d={SHIELD}
        fill="none"
        stroke={ink}
        strokeOpacity=".28"
        strokeWidth="1.4"
        transform="translate(2.4 2.6) scale(0.88)"
      />
      {symbol && (
        <path
          d={symbol.path}
          transform={place}
          fill={"line" in symbol ? "none" : ink}
          stroke={ink}
          strokeWidth={"line" in symbol ? 2.2 : 0.6}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      {lettered && (
        <text
          x="20"
          y={symbol ? 34 : 26.5}
          textAnchor="middle"
          style={{ fill: ink }}
          className={symbol ? "" : "alone"}
        >
          {code}
        </text>
      )}
    </svg>
  );
}

/** A nation's flag, or a club's badge. We hold no official logos: the badges are our own. */
export function Crest({ team, size = "" }: { team: string; size?: Size }) {
  const flag = flagOf(team);
  // The picture is decoration: the team's name is always written beside it.
  if (flag) return <img className={`crest flag ${size}`} src={flag} alt="" loading="lazy" />;
  return <Badge team={team} size={size} />;
}

/** A player's initials in a neutral roundel. We hold no photographs. */
export function Face({ name, size = "" }: { name: string; size?: Size }) {
  const words = name.split(/\s+/);
  const last = words.length > 1 ? words[words.length - 1][0] : "";
  const initials = (words[0][0] + last).toUpperCase();
  return (
    <span className={`crest face ${size}`} aria-hidden="true">
      {initials}
    </span>
  );
}

export function PlayerLink({ sport, id, name }: { sport: Sport; id: string; name: string }) {
  return <Link href={link(sport, "player", id)}>{name}</Link>;
}

export function TeamLink({ sport, league, team }: { sport: Sport; league: string; team: string }) {
  return <Link href={teamHref(sport, league, team)}>{team}</Link>;
}

interface PlayerRowProps {
  sport: Sport;
  player: { player_id: string; name: string };
  small: ReactNode;
  value: ReactNode;
}

/** A row that links to a player: roundel, name with a small line under it, and a value. */
export function PlayerRow({ sport, player, small, value }: PlayerRowProps) {
  return (
    <Link className="rowlink" href={link(sport, "player", player.player_id)}>
      <Face name={player.name} />
      <span>
        <b>{player.name}</b>
        <small>{small}</small>
      </span>
      <span className="val">{value}</span>
    </Link>
  );
}
