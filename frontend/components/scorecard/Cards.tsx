// The batting and bowling cards of one innings, as a printed scorecard lays them out.

import Link from "next/link";

import { num } from "@/lib/format";
import { link } from "@/lib/sport";

import { type InningsCard, total } from "./types";

function BattingCard({ innings }: { innings: InningsCard }) {
  const { extras } = innings;
  const extrasDetail = [
    extras.byes ? `b/lb ${extras.byes}` : "",
    extras.wides ? `w ${extras.wides}` : "",
    extras.no_balls ? `nb ${extras.no_balls}` : "",
  ]
    .filter(Boolean)
    .join(", ");
  return (
    <div className="scroll">
      <table className="card-table">
        <thead>
          <tr>
            <th className="l">Batting</th>
            <th>R</th>
            <th>B</th>
            <th>4s</th>
            <th>6s</th>
            <th>SR</th>
          </tr>
        </thead>
        <tbody>
          {innings.batting.map((line) => (
            <tr key={line.player_id}>
              <td className="l">
                <Link className={line.out ? "" : "strong"} href={link("ck", "player", line.player_id)}>
                  {line.name}
                </Link>
                <small>{line.how}</small>
              </td>
              <td>
                <b>{line.runs}</b>
              </td>
              <td>{line.balls}</td>
              <td>{line.fours}</td>
              <td>{line.sixes}</td>
              <td>{num(line.strike_rate, 1)}</td>
            </tr>
          ))}
          <tr>
            <td className="l">
              Extras<small>{extrasDetail}</small>
            </td>
            <td>{extras.total}</td>
            <td colSpan={4}></td>
          </tr>
          <tr className="total">
            <td className="l">
              Total<small>{innings.overs} overs</small>
            </td>
            <td>{total(innings)}</td>
            <td colSpan={4}></td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function BowlingCard({ innings }: { innings: InningsCard }) {
  return (
    <div className="scroll">
      <table className="card-table">
        <thead>
          <tr>
            <th className="l">Bowling</th>
            <th>O</th>
            <th>M</th>
            <th>R</th>
            <th>W</th>
            <th>Econ</th>
          </tr>
        </thead>
        <tbody>
          {innings.bowling.map((line) => (
            <tr key={line.player_id}>
              <td className="l">
                <Link href={link("ck", "player", line.player_id)}>{line.name}</Link>
              </td>
              <td>{line.overs}</td>
              <td>{line.maidens}</td>
              <td>{line.runs}</td>
              <td>
                <b>{line.wickets}</b>
              </td>
              <td>{num(line.economy, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Cards({ innings }: { innings: InningsCard }) {
  return (
    <>
      <div className="cols2 cards">
        <BattingCard innings={innings} />
        <BowlingCard innings={innings} />
      </div>
      {innings.did_not_bat.length > 0 && (
        <p className="note">
          <b>Did not bat:</b> {innings.did_not_bat.join(", ")}
        </p>
      )}
      {innings.fall_of_wickets.length > 0 && (
        <p className="note">
          <b>Fall of wickets:</b>{" "}
          {innings.fall_of_wickets
            .map((fall) => `${fall.wicket}–${fall.score} (${fall.name}, ${fall.over} ov)`)
            .join(", ")}
        </p>
      )}
    </>
  );
}
