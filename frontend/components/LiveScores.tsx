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
  if (!scores.matches.length) return <p className="note">No matches are being played right now.</p>;
  // Matches under way get a scorebox each. Those yet to start are only fixtures: one line each.
  const playing = scores.matches.filter((match) => match.started).slice(0, limit);
  const coming = scores.matches
    .filter((match) => !match.started)
    .slice(0, limit ? limit - playing.length : undefined);
  return (
    <>
      {playing.length > 0 && (
        <div className={grid ? "live-grid" : ""}>
          {playing.map((match) => (
            <Match key={match.link} match={match} />
          ))}
        </div>
      )}
      {coming.length > 0 && (
        <>
          <p className="sb-label coming-label">Coming up</p>
          <div className={`fixtures ${grid ? "grid" : ""}`}>
            {coming.map((match) => (
              <a
                key={match.link}
                className="fixture"
                href={match.link}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Crest team={siteTeamName(match.first.team)} size="sm" />
                <span>
                  {match.first.team} <i>v</i> {match.second.team}
                </span>
                <Crest team={siteTeamName(match.second.team)} size="sm" />
              </a>
            ))}
          </div>
        </>
      )}
      <p className="note">
        Live scores from {scores.source}, read every two minutes. A row opens the match on their site.
      </p>
    </>
  );
}
