// Matches as they appear across the site: a score box, a story card, a table row.

import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import { WORDS, day, num } from "@/lib/format";
import { isLong, splitLine } from "@/lib/score";
import { type Sport, link } from "@/lib/sport";
import { identity } from "@/lib/teams";
import { tip } from "@/lib/toast";
import type { MatchSummary } from "@/lib/types";

import { Crest, TeamLink } from "./teams";

type Scored = Pick<
  MatchSummary,
  "sport" | "league" | "team1" | "team2" | "score1" | "score2" | "winner" | "line1" | "line2" | "art"
>;

/** A side's score: its written line when there is one, else the bare runs. */
function scoreOf(line: string | null | undefined, score: number | null) {
  return line ? splitLine(line) : { runs: score == null ? "" : num(score), overs: "" };
}

const lostClass = (match: Scored, team: string) =>
  match.winner && match.winner !== team ? "lose" : "";

interface ScoreboxProps {
  match: Scored;
  big?: boolean;
  linked?: boolean;
}

/** Two teams and their scores, one per line, written 155/8 (20 ov). The loser is dimmed. */
export function Scorebox({ match, big = false, linked = false }: ScoreboxProps) {
  const row = (team: string, line: string | null | undefined, score: number | null) => {
    const lost = lostClass(match, team);
    const { runs, overs } = scoreOf(line, score);
    return (
      <>
        <Crest team={team} size={big ? "lg" : ""} />
        <span className={`name ${lost}`}>
          {linked ? <TeamLink sport={match.sport} league={match.league} team={team} /> : team}
        </span>
        <span className={`runs ${lost} ${isLong(line) ? "long" : ""}`}>
          {runs}
          {overs && <small> ({overs})</small>}
        </span>
      </>
    );
  };
  return (
    <div className={`scorebox ${big ? "big" : ""}`}>
      {row(match.team1, match.line1, match.score1)}
      {row(match.team2, match.line2, match.score2)}
    </div>
  );
}

/**
 * The picture slot of a story card. We have no photographs, so it shows the two teams'
 * colours, their codes as a watermark, and the score on top.
 */
export function Media({
  match,
  wide = false,
  tag = "",
}: {
  match: Scored;
  wide?: boolean;
  tag?: string;
}) {
  const first = identity(match.team1);
  const second = identity(match.team2);
  const side = (team: string, line: string | null | undefined, score: number | null, code: string) => {
    const lost = lostClass(match, team);
    if (score == null && !line) return <span className={lost}>{code}</span>;
    const { runs, overs } = scoreOf(line, score);
    return (
      <span className={`${lost} ${isLong(line) ? "long" : ""}`}>
        {runs}
        <small>
          {code}
          {overs && ` · ${overs}`}
        </small>
      </span>
    );
  };
  const colors = { "--a": first.color, "--b": second.color } as CSSProperties;
  return (
    <div className={`media ${wide ? "wide" : ""}`} style={colors}>
      {/* A grey 3D render (animation/card_*.py). The page tints it with the two teams' colours. */}
      {match.art && <img className="art" src={`/cards/${match.art}.webp`} alt="" loading="lazy" />}
      {tag && <span className="chip tag">{tag}</span>}
      <span className="wm l">{first.code}</span>
      <span className="wm r">{second.code}</span>
      <div className="line">
        {side(match.team1, match.line1, match.score1, first.code)}
        <span className="dash">–</span>
        {side(match.team2, match.line2, match.score2, second.code)}
      </div>
    </div>
  );
}

/** A card that links to a match: picture, label, headline, date. */
export function StoryCard({ match, label }: { match: MatchSummary; label?: ReactNode }) {
  return (
    <Link className="card" href={link(match.sport, "match", match.match_id)}>
      <Media match={match} />
      <div className="body">
        {label && <p className="kicker">{label}</p>}
        <h3>{match.headline || `${match.team1} v ${match.team2}`}</h3>
        {match.result && <p className="result-line">{match.result}</p>}
        <p className="dek">
          {day(match.date)} · {match.league}
        </p>
      </div>
    </Link>
  );
}

/** The thrill score as a chip, with a tooltip that says what it means. */
export function ThrillChip({ match }: { match: Pick<MatchSummary, "thrill" | "league"> }) {
  if (match.thrill == null) return null;
  const meaning = `How far the win chance swung, against other ${match.league} games. 10 is the wildest.`;
  return (
    <span className="chip" {...tip("Thrill score", meaning)}>
      Thrill {num(match.thrill * 10, 1)}
    </span>
  );
}

/** A plain list of matches: date, both sides with their scores, the result, thrill and league. */
export function MatchTable({ sport, matches }: { sport: Sport; matches: MatchSummary[] }) {
  const words = WORDS[sport];
  const side = (
    match: MatchSummary,
    team: string,
    line: string | null | undefined,
    score: number | null,
  ) => {
    const won = match.winner === team ? "win" : "";
    const { runs, overs } = scoreOf(line, score);
    return (
      <>
        <td className={`l ${won}`}>
          <Crest team={team} size="sm" />
          <TeamLink sport={sport} league={match.league} team={team} />
        </td>
        <td className={`score-cell ${won}`}>
          {runs}
          {overs && <small> ({overs})</small>}
        </td>
      </>
    );
  };
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th className="l">Date</th>
            <th className="l">{words.first}</th>
            <th></th>
            <th className="l">{words.second}</th>
            <th></th>
            <th className="l">Result</th>
            <th>Thrill</th>
            <th className="l">League</th>
          </tr>
        </thead>
        <tbody>
          {matches.map((match) => (
            <tr key={match.match_id}>
              <td className="l">
                <Link className="u" href={link(sport, "match", match.match_id)}>
                  {day(match.date)}
                </Link>
              </td>
              {side(match, match.team1, match.line1, match.score1)}
              {side(match, match.team2, match.line2, match.score2)}
              <td className="l sub">{shortResult(match)}</td>
              <td>{match.thrill == null ? "–" : num(match.thrill * 10, 1)}</td>
              <td className="l dim">{match.league}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The result with the winner's code in place of the full name, to fit a table: "RCB won by 5 wickets". */
export function shortResult(match: Pick<MatchSummary, "result" | "winner">): string {
  if (!match.result) return "";
  return match.winner ? match.result.replace(match.winner, identity(match.winner).code) : match.result;
}
