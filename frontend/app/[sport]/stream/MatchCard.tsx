// One match as a cricket scoreboard: the score, the chase, the batters and bowler, this over,
// the win probability and the worm.

"use client";

import { Crest } from "@/components/teams";
import {
  type Card,
  type LiveMatch,
  type Point,
  inningsScore,
  isOver,
  overs,
  runRate,
  status,
} from "@/lib/stream";
import { identity } from "@/lib/teams";

import { Worm } from "./Worm";

const FULL: Record<string, number> = { T20: 120, ODI: 300 };
const code = (team: string) => identity(team).code;

function Side({
  team,
  at,
  full,
  batting,
}: {
  team: string;
  at: Point | null;
  full: number;
  batting: boolean;
}) {
  return (
    <div className={`sb-side ${batting ? "at-bat" : ""}`}>
      <Crest team={team} size="sm" />
      <span title={team}>{code(team)}</span>
      {at ? (
        <b>
          {at.score}/{at.wickets} <small>({overs(full - at.balls_left)})</small>
        </b>
      ) : (
        <small>Yet to bat</small>
      )}
    </div>
  );
}

function Rates({ last, full }: { last: Point; full: number }) {
  const bowled = full - last.balls_left;
  const parts = [`CRR ${runRate(last.score, bowled)}`];
  if (last.innings === 2 && last.target != null && last.balls_left > 0)
    parts.push(`RRR ${runRate(last.target - last.score, last.balls_left)}`);
  return <p className="sb-rates">{parts.join("  ·  ")}</p>;
}

/** Win probability as a split bar in the two teams' colours. */
function WinBar({ match, chance }: { match: LiveMatch; chance: number }) {
  const [one, two] = [identity(match.team1), identity(match.team2)];
  const share = Math.round(chance * 100);
  return (
    <div className="sb-win">
      <span className="sb-label">Win probability</span>
      <div className="sb-win-row">
        <b>
          {one.code} {share}%
        </b>
        <div className="sb-win-bar">
          <i style={{ width: `${share}%`, background: one.color }} />
          <i style={{ width: `${100 - share}%`, background: two.color }} />
        </div>
        <b>
          {100 - share}% {two.code}
        </b>
      </div>
    </div>
  );
}

function Crease({ card }: { card: Card }) {
  return (
    <table className="sb-table">
      <thead>
        <tr>
          <th className="l">Batter</th>
          <th>R</th>
          <th>B</th>
          <th>4s</th>
          <th>6s</th>
        </tr>
      </thead>
      <tbody>
        {card.batters.map((batter) => (
          <tr key={batter.name}>
            <td className="l">
              {batter.name}
              {batter.on_strike ? " *" : ""}
            </td>
            <td>
              <b>{batter.runs}</b>
            </td>
            <td>{batter.balls}</td>
            <td>{batter.fours}</td>
            <td>{batter.sixes}</td>
          </tr>
        ))}
        {card.bowler && (
          <tr className="sb-bowler">
            <td className="l">{card.bowler.name}</td>
            <td colSpan={4}>{card.bowler.figures}</td>
          </tr>
        )}
      </tbody>
    </table>
  );
}

/** The balls of the over now being bowled, as small marks: • 1 4 6 W wd. */
function ThisOver({ marks }: { marks: string[] }) {
  return (
    <div className="sb-over">
      <span className="sb-label">This over</span>
      {marks.map((mark, at) => (
        <i key={at} className={`ball b-${mark.replace(/^\d+/, "") || mark}`}>
          {mark}
        </i>
      ))}
    </div>
  );
}

export function MatchCard({ match }: { match: LiveMatch }) {
  const last = match.points.at(-1);
  const full = FULL[match.fmt] ?? 120;
  const ball = match.points.findLast((point) => point.kind === "ball");
  const card = ball?.card;
  const over = isOver(match);
  const batting = last && !over ? last.bat_team : null;
  return (
    <article className={`card live-card ${over ? "over" : ""}`}>
      <div className="body">
        <p className="kicker quiet">
          <span className="live-dot" aria-hidden="true" />
          {over ? "Result" : "Live"}
          <span className="sep">{match.competition}</span>
        </p>
        <Side
          team={match.team1}
          at={inningsScore(match, 1)}
          full={full}
          batting={batting === match.team1}
        />
        <Side
          team={match.team2}
          at={inningsScore(match, 2)}
          full={full}
          batting={batting === match.team2}
        />
        {last && <p className="sb-status">{status(match, last, code)}</p>}
        {last && !over && last.kind === "ball" && <Rates last={last} full={full} />}
        {last && <WinBar match={match} chance={last.wp1} />}
        <Worm match={match} />
        {card && !over && last?.kind === "ball" && (
          <>
            <Crease card={card} />
            <p className="sb-small">
              Partnership {card.partnership[0]} ({card.partnership[1]})
              {card.last_wicket ? `  ·  Last wicket: ${card.last_wicket}` : ""}
            </p>
            <ThisOver marks={card.this_over} />
          </>
        )}
        {/* A new key makes each ball's line fade in afresh. */}
        <p className="live-ball" key={ball?.n ?? 0}>
          {ball ? (
            <>
              <b>{ball.at}</b> {ball.text}
            </>
          ) : (
            "The players are walking out."
          )}
        </p>
      </div>
    </article>
  );
}
