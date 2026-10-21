// The public record: tally, league table, worst misses and the latest calls. All server-drawn.

import Link from "next/link";

import { Crest } from "@/components/teams";
import { day, num, pct, signed } from "@/lib/format";
import { type Sport, link } from "@/lib/sport";

import type { Call, LeagueTally, Tally } from "./types";

const percentRight = (tally: Tally) => `${num((100 * tally.right) / tally.n, 1)}%`;

export function RecordTiles({ record }: { record: Tally }) {
  return (
    <>
      <h2 className="label">The record</h2>
      <div className="tiles">
        <div className="tile">
          <b>{num(record.n)}</b>
          <span>calls scored</span>
        </div>
        <div className="tile">
          <b>{percentRight(record)}</b>
          <span>right</span>
        </div>
        <div className="tile">
          <b>{signed(record.per_call, 2)}</b>
          <span>points per call. A coin flip is 0</span>
        </div>
      </div>
    </>
  );
}

export function ByLeague({ leagues }: { leagues: LeagueTally[] }) {
  return (
    <section>
      <h2 className="label">By league</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th className="l">League</th>
              <th>Calls</th>
              <th>Right</th>
              <th>Points per call</th>
            </tr>
          </thead>
          <tbody>
            {leagues.map((league) => (
              <tr key={league.league}>
                <td className="l">{league.league}</td>
                <td>{num(league.n)}</td>
                <td>{percentRight(league)}</td>
                <td>{signed(league.per_call, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Miss({ sport, call }: { sport: Sport; call: Call }) {
  return (
    <Link className="play" href={link(sport, "match", call.id)}>
      <span className="when">
        {day(call.date).replace(/, \d+$/, "")}
        <br />
        {call.date.slice(0, 4)}
      </span>
      <span className="what">
        We gave {call.pick} {pct(call.conf)}. {call.winner} won.
        <small>
          {call.team1} v {call.team2} · {call.league}
        </small>
      </span>
      <span className="swing">{signed(call.points, 0)}</span>
    </Link>
  );
}

export function WorstMisses({ sport, misses }: { sport: Sport; misses: Call[] }) {
  return (
    <>
      <h2 className="label">Our worst misses</h2>
      <div className="plays">
        {misses.map((call) => (
          <Miss key={call.id} sport={sport} call={call} />
        ))}
      </div>
    </>
  );
}

function CallRow({ sport, call }: { sport: Sport; call: Call }) {
  return (
    <tr>
      <td className="l">{day(call.date)}</td>
      <td className="l">
        <Link className="u" href={link(sport, "match", call.id)}>
          {call.team1} v {call.team2}
        </Link>
      </td>
      <td className="l">
        <Crest team={call.pick} size="sm" />
        {call.pick}
      </td>
      <td>{pct(call.conf)}</td>
      <td className={`l ${call.right ? "win" : ""}`}>{call.winner}</td>
      <td>{signed(call.points, 0)}</td>
    </tr>
  );
}

export function LatestCalls({ sport, calls }: { sport: Sport; calls: Call[] }) {
  return (
    <>
      <h2 className="label">Latest calls</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th className="l">Date</th>
              <th className="l">Match</th>
              <th className="l">Our call</th>
              <th></th>
              <th className="l">Winner</th>
              <th>Points</th>
            </tr>
          </thead>
          <tbody>
            {calls.map((call) => (
              <CallRow key={call.id} sport={sport} call={call} />
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">
        Each call was made only from data before the match, in a season the model never trained on.
      </p>
    </>
  );
}
