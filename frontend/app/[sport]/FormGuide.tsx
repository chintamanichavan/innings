// The form guide: who is hot and who is cold over the last ten games, for one league.

"use client";

import { Options, useSetQuery } from "@/components/controls";
import { PlayerRow } from "@/components/teams";
import { WORDS, num, signed } from "@/lib/format";
import type { Sport } from "@/lib/sport";

import type { FormPlayer, Home } from "./types";

function FormList({ sport, players, unit }: { sport: Sport; players: FormPlayer[]; unit: string }) {
  if (!players.length) return <p className="empty">Nobody qualifies yet.</p>;
  return (
    <div className="rows">
      {players.map((player) => (
        <PlayerRow
          key={player.player_id}
          sport={sport}
          player={player}
          small={`${num(player.n)} ${unit}`}
          value={signed(player.value, 1)}
        />
      ))}
    </div>
  );
}

export function FormGuide({ sport, home }: { sport: Sport; home: Home }) {
  const words = WORDS[sport];
  const setQuery = useSetQuery();
  return (
    <>
      <h2 className="label">Form guide · last 10 games</h2>
      <div className="filters">
        <select
          aria-label="League"
          value={home.hot_league}
          onChange={(event) => setQuery({ hot: event.target.value })}
        >
          <Options items={home.hot_leagues} />
        </select>
        <span className="note flush">Runs added above an average player.</span>
      </div>
      <div className="cols3">
        <section>
          <p className="kicker">Hot bats</p>
          <FormList sport={sport} players={home.hot_bat} unit={words.chances} />
        </section>
        <section>
          <p className="kicker">Hot {words.bowl.toLowerCase()}</p>
          <FormList sport={sport} players={home.hot_bowl} unit={words.faced} />
        </section>
        <section>
          <p className="kicker quiet">Out of form</p>
          <FormList sport={sport} players={home.cold_bat} unit={words.chances} />
        </section>
      </div>
    </>
  );
}
