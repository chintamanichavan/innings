// Who decided the match, and every player's share, by win chance added.

import { PlayerLink, PlayerRow } from "@/components/teams";
import { signed } from "@/lib/format";
import type { Sport } from "@/lib/sport";

import type { PlayerLine } from "./types";

const WINNERS_SHOWN = 3;
const LOSERS_SHOWN = 2;

function Row({ sport, player }: { sport: Sport; player: PlayerLine }) {
  const value = signed(player.wpa * 100, 0);
  return <PlayerRow sport={sport} player={player} small={player.line || ""} value={value} />;
}

export function WhoDecidedIt({ sport, players }: { sport: Sport; players: PlayerLine[] }) {
  const winners = players.slice(0, WINNERS_SHOWN);
  const losers = players.slice(-LOSERS_SHOWN).reverse();
  return (
    <section>
      <h2 className="label">Who won it</h2>
      <div className="rows">
        {winners.map((p) => (
          <Row key={p.player_id} sport={sport} player={p} />
        ))}
      </div>
      <h2 className="label">Who lost it</h2>
      <div className="rows">
        {losers.map((p) => (
          <Row key={p.player_id} sport={sport} player={p} />
        ))}
      </div>
      <p className="note">Points of win chance each player added or gave away.</p>
    </section>
  );
}

export function Everyone({ sport, players }: { sport: Sport; players: PlayerLine[] }) {
  return (
    <>
      <h2 className="label">Everyone, by win chance added</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th className="l">Player</th>
              <th>Win chance added</th>
              <th>Runs above average</th>
            </tr>
          </thead>
          <tbody>
            {players.map((player) => (
              <tr key={player.player_id}>
                <td className="l">
                  <PlayerLink sport={sport} id={player.player_id} name={player.name} />
                </td>
                <td>{signed(player.wpa * 100, 1)}</td>
                <td>{signed(player.rae, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
