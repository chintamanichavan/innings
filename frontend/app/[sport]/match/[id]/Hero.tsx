// The top of the match page: score, headline, standfirst, our pre-match call and the chips.

import Link from "next/link";

import { ShareButton } from "@/components/controls";
import { Marked } from "@/components/Marked";
import { Media, ThrillChip } from "@/components/matches";
import { day, num, pct } from "@/lib/format";
import { type Sport, link, teamHref } from "@/lib/sport";

import type { MatchDetail, MatchPage, PlayerLine } from "./types";

interface HeroProps {
  sport: Sport;
  match: MatchDetail;
  story: MatchPage["story"];
  call: MatchPage["call"];
  star: PlayerLine | null; // the player who added the most win chance
}

/** What we said before the match, and whether it came true. */
type Call = NonNullable<MatchPage["call"]>;

function OurCall({ sport, match, call }: { sport: Sport; match: MatchDetail; call: Call }) {
  const favoured = call.p1 >= 0.5 ? match.team1 : match.team2;
  const confidence = pct(Math.max(call.p1, 1 - call.p1));
  let verdict = "";
  if (match.winner) verdict = favoured === match.winner ? "We were right." : "We were wrong.";
  return (
    <p className="sub spaced">
      <Marked text={`Before the match we gave ${favoured} ${confidence}.`} /> {verdict}{" "}
      <Link className="u" href={link(sport, "forecasts")}>
        Our full record
      </Link>
    </p>
  );
}

function Chips({ sport, match, headline }: { sport: Sport; match: MatchDetail; headline: string }) {
  const changes = match.lead_changes;
  const teamChip = (team: string) => (
    <Link className="chip" href={teamHref(sport, match.league, team)}>
      {team}
    </Link>
  );
  return (
    <div className="meta">
      {teamChip(match.team1)}
      {teamChip(match.team2)}
      <ThrillChip match={match} />
      {changes != null && (
        <span className="chip">
          {changes} change{changes === 1 ? "" : "s"} of favourite
        </span>
      )}
      {match.winner_low != null && (
        <span className="chip">Winner&apos;s lowest point {num(match.winner_low * 100, 1)}%</span>
      )}
      <ShareButton title={headline} />
    </div>
  );
}

/** Our player of the match: whoever added the most win chance, with their line from the game. */
function Star({ sport, star }: { sport: Sport; star: PlayerLine }) {
  return (
    <p className="star">
      <span className="sb-label">Player of the match</span>
      <Link className="u" href={link(sport, "player", star.player_id)}>
        {star.name}
      </Link>
      {star.line && <span> · {star.line}</span>}
      <span className="dim"> · +{num(star.wpa * 100)} points of win chance</span>
    </p>
  );
}

export function Hero({ sport, match, story, call, star }: HeroProps) {
  return (
    <div className="card hero story-hero">
      <Media match={match} wide />
      <div className="body">
        <p className="kicker">
          {match.league} <span className="sep">{day(match.date)}</span>
          {match.venue && (
            <span className="sep">
              <Link href={link(sport, "venue", match.venue)}>{match.venue}</Link>
            </span>
          )}
        </p>
        {match.result && <p className="result-line big">{match.result}</p>}
        <h1>{story.headline}</h1>
        <p className="standfirst">
          <Marked text={story.standfirst} />
        </p>
        {star && star.wpa > 0 && <Star sport={sport} star={star} />}
        {call && <OurCall sport={sport} match={match} call={call} />}
        <Chips sport={sport} match={match} headline={story.headline} />
      </div>
    </div>
  );
}
