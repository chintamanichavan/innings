// "Plays most like": the cricketers whose skills sit closest to this player's.

import Link from "next/link";

import { Face } from "@/components/teams";
import { num } from "@/lib/format";
import { type Sport, link } from "@/lib/sport";

import type { Alike } from "./types";

/** Each row opens the two players side by side. */
export function MostAlike({ sport, id, alike }: { sport: Sport; id: string; alike: Alike[] }) {
  if (!alike.length) return null;
  return (
    <section>
      <h2 className="label">Plays most like</h2>
      <div className="rows narrow">
        {alike.map((other) => (
          <Link
            className="rowlink"
            key={other.player_id}
            href={link(sport, "compare", "", { a: id, b: other.player_id })}
          >
            <Face name={other.name} />
            <span>
              <b>{other.name}</b>
              <small>{other.fmt} cricket</small>
            </span>
            <span className="val">{num(other.match)}%</span>
          </Link>
        ))}
      </div>
      <p className="note">How alike two players are across the same five skills, out of 100.</p>
    </section>
  );
}
