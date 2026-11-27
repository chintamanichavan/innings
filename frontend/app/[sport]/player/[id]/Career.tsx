// The top of a profile, as every cricket site opens one: a career summary by format, then
// the player's latest matches.

import Link from "next/link";

import { day, num } from "@/lib/format";
import { type Sport, link } from "@/lib/sport";

import type { BattingLine, BowlingLine, Career, RecentGame } from "./types";

const dash = (value: number | null, digits = 2) => (value == null ? "–" : num(value, digits));

function Batting({ rows }: { rows: BattingLine[] }) {
  return (
    <div className="scroll">
      <table className="career">
        <thead>
          <tr>
            <th className="l">Batting</th>
            <th>Mat</th>
            <th>Inns</th>
            <th>NO</th>
            <th>Runs</th>
            <th>HS</th>
            <th>Ave</th>
            <th>BF</th>
            <th>SR</th>
            <th>100s</th>
            <th>50s</th>
            <th>4s</th>
            <th>6s</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.league}>
              <td className="l">{row.league}</td>
              <td>{row.matches}</td>
              <td>{row.innings}</td>
              <td>{row.not_outs}</td>
              <td>
                <b>{num(row.runs)}</b>
              </td>
              <td>{row.best}</td>
              <td>{dash(row.average)}</td>
              <td>{num(row.balls)}</td>
              <td>{dash(row.strike_rate)}</td>
              <td>{row.hundreds}</td>
              <td>{row.fifties}</td>
              <td>{num(row.fours)}</td>
              <td>{num(row.sixes)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Bowling({ rows }: { rows: BowlingLine[] }) {
  return (
    <div className="scroll">
      <table className="career">
        <thead>
          <tr>
            <th className="l">Bowling</th>
            <th>Mat</th>
            <th>Inns</th>
            <th>Balls</th>
            <th>Runs</th>
            <th>Wkts</th>
            <th>BBI</th>
            <th>Ave</th>
            <th>Econ</th>
            <th>SR</th>
            <th>4w</th>
            <th>5w</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.league}>
              <td className="l">{row.league}</td>
              <td>{row.matches}</td>
              <td>{row.innings}</td>
              <td>{num(row.balls)}</td>
              <td>{num(row.runs)}</td>
              <td>
                <b>{row.wickets}</b>
              </td>
              <td>{row.best}</td>
              <td>{dash(row.average)}</td>
              <td>{dash(row.economy)}</td>
              <td>{dash(row.strike_rate, 1)}</td>
              <td>{row.fours}</td>
              <td>{row.fives}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * One recent match: "73 (49)" with the bat, "2/24 (4)" with the ball, against whom. The
 * player's main skill comes first and large; the other follows small, when there is one.
 */
function Recent({ sport, games, bowler }: { sport: Sport; games: RecentGame[]; bowler: boolean }) {
  return (
    <div className="form-strip">
      {games.map((game) => {
        const overs = `${Math.floor(game.bowled / 6)}${game.bowled % 6 ? `.${game.bowled % 6}` : ""}`;
        const batting = game.batted ? (
          <>
            {game.runs}
            {game.out ? "" : "*"} <small>({game.faced})</small>
          </>
        ) : null;
        const bowling =
          game.bowled > 0 ? (
            <>
              {game.wickets}/{game.conceded} <small>({overs})</small>
            </>
          ) : null;
        const [main, other] = bowler ? [bowling, batting] : [batting, bowling];
        return (
          <Link key={game.match_id} className="form-game" href={link(sport, "match", game.match_id)}>
            {main ? <b>{main}</b> : <b className="dim">{bowler ? "Did not bowl" : "DNB"}</b>}
            {other && <span>{other}</span>}
            <small>
              v {game.opponent} · {game.league}
            </small>
            <small className="dim">{day(game.date)}</small>
          </Link>
        );
      })}
    </div>
  );
}

interface CareerProps {
  sport: Sport;
  career: Career;
  bowler: boolean; // a bowler's page shows bowling first
}

export function CareerSummary({ sport, career, bowler }: CareerProps) {
  const batting = career.batting.length > 0 && <Batting rows={career.batting} />;
  const bowling = career.bowling.length > 0 && <Bowling rows={career.bowling} />;
  return (
    <>
      <h2 className="label">Career summary</h2>
      {bowler ? bowling : batting}
      {bowler ? batting : bowling}
      <p className="note">
        From ball-by-ball records, which start in the early 2000s; an older career is cut short.
      </p>
      {career.recent.length > 0 && (
        <>
          <h2 className="label">Recent form</h2>
          <Recent sport={sport} games={career.recent} bowler={bowler} />
        </>
      )}
    </>
  );
}
