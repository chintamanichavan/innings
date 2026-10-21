// The live scoreboard: matches in progress, re-read from the feed every two minutes.

"use client";

import { useEffect, useState } from "react";

import { Crest } from "@/components/teams";
import { api } from "@/lib/api";
import { type LiveMatch, type LiveScores as Scores, type LiveSide, siteTeamName } from "@/lib/news";

const REFRESH_MS = 120_000; // the feed asks readers to wait two minutes between reads

function Side({ side }: { side: LiveSide }) {
  return (
    <>
      <Crest team={siteTeamName(side.team)} />
      <span className="name">
        {side.team}
        {side.batting && <i className="batting" title="Batting now" />}
      </span>
      <span className="runs">{side.score}</span>
    </>
  );
}

function Match({ match }: { match: LiveMatch }) {
  return (
    <a className="score-link live" href={match.link} target="_blank" rel="noopener noreferrer">
      <div className="scorebox">
        <Side side={match.first} />
        <Side side={match.second} />
      </div>
      {!match.started && <div className="meta">Yet to start</div>}
    </a>
  );
}

interface LiveScoresProps {
  limit?: number; // show at most this many matches
  grid?: boolean; // lay the matches out side by side, for a full page
}

/** Draws nothing until the feed has answered, and nothing if it has no matches. */
export function LiveScores({ limit, grid = false }: LiveScoresProps) {
  const [scores, setScores] = useState<Scores | null>(null);

  useEffect(() => {
    let current = true;
    const read = () =>
      api<Scores>("livescores")
        .then((next) => current && setScores(next))
        .catch(() => {});
    read();
    const timer = setInterval(read, REFRESH_MS);
    return () => {
      current = false;
      clearInterval(timer);
    };
  }, []);

  if (!scores) return null;
  if (!scores.ok) return <p className="note">The live scores feed is not answering just now.</p>;
  const matches = scores.matches.slice(0, limit);
  if (!matches.length) return <p className="note">No matches are being played right now.</p>;
  return (
    <>
      <div className={grid ? "live-grid" : ""}>
        {matches.map((match) => (
          <Match key={match.link} match={match} />
        ))}
      </div>
      <p className="note">
        Live scores from {scores.source}, read every two minutes. A row opens the match on their site.
      </p>
    </>
  );
}
