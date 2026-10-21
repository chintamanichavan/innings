// The plays that moved the win chance most.

import { pct } from "@/lib/format";

import type { MatchDetail, Play } from "./types";

const INNINGS_NAMES = ["1st", "2nd", "3rd", "4th"];
const BIG_MOMENTS = 8;

const swing = (play: Play) => Math.abs(play.wp1_post - play.wp1);

function When({ play }: { play: Play }) {
  return (
    <>
      {INNINGS_NAMES[play.period - 1]} inns
      <br />
      {play.at}
    </>
  );
}

export function Plays({ match, events }: { match: MatchDetail; events: Play[] }) {
  const biggest = [...events].sort((a, b) => swing(b) - swing(a)).slice(0, BIG_MOMENTS);
  const inOrder = biggest.sort((a, b) => a.seq - b.seq);
  return (
    <section>
      <h2 className="label">The moments that moved it</h2>
      <div className="plays">
        {inOrder.map((play) => (
          <div className="play" key={play.seq}>
            <span className="when">
              <When play={play} />
            </span>
            <span className="what">
              {play.text}
              <small>{play.score}</small>
            </span>
            <span className="swing">
              {pct(play.wp1)} → {pct(play.wp1_post)}
            </span>
          </div>
        ))}
      </div>
      <p className="note">Percentages are {match.team1}&apos;s chance of winning before and after.</p>
    </section>
  );
}
