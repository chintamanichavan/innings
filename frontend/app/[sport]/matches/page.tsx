// Every match in a league and year, optionally for one team.

import type { Metadata } from "next";
import Link from "next/link";

import { Crest, TeamLink } from "@/components/teams";
import { api } from "@/lib/api";
import { WORDS, day, num } from "@/lib/format";
import { leaguesOf } from "@/lib/meta";
import { type PageProps, readPage } from "@/lib/page";
import { type Sport, link } from "@/lib/sport";
import { yearsOf } from "@/lib/types";

import { Filters } from "./Filters";
import type { MatchRow } from "./types";

const LIST_LIMIT = 1000;

export async function generateMetadata(props: PageProps): Promise<Metadata> {
  const { q } = await readPage(props);
  return { title: q.team || "Every game" };
}

function SideCells({
  sport,
  league,
  match,
  team,
  score,
}: {
  sport: Sport;
  league: string;
  match: MatchRow;
  team: string;
  score: number;
}) {
  const won = match.winner === team ? "win" : "";
  return (
    <>
      <td className={`l ${won}`}>
        <Crest team={team} size="sm" />
        <TeamLink sport={sport} league={league} team={team} />
      </td>
      <td className={won}>{num(score)}</td>
    </>
  );
}

function MatchList({ sport, league, list }: { sport: Sport; league: string; list: MatchRow[] }) {
  if (!list.length) return <p className="empty">No matches for this choice.</p>;
  const words = WORDS[sport];
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
            <th className="l">Venue</th>
          </tr>
        </thead>
        <tbody>
          {list.map((match) => (
            <tr key={match.match_id}>
              <td className="l">
                <Link className="u" href={link(sport, "match", match.match_id)}>
                  {day(match.date)}
                </Link>
              </td>
              <SideCells
                sport={sport}
                league={league}
                match={match}
                team={match.team1}
                score={match.score1}
              />
              <SideCells
                sport={sport}
                league={league}
                match={match}
                team={match.team2}
                score={match.score2}
              />
              <td className="l sub">{match.note || ""}</td>
              <td className="l dim">
                {match.venue && <Link href={link(sport, "venue", match.venue)}>{match.venue}</Link>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function Matches(props: PageProps) {
  const { sport, q } = await readPage(props);
  const leagues = await leaguesOf(sport);
  const league = q.league || leagues[0].league;
  const leagueInfo = leagues.find((item) => item.league === league) || leagues[0];
  const year = q.year || leagueInfo.last;
  const [list, teams] = await Promise.all([
    api<MatchRow[]>("matches", { sport, league, year, team: q.team, limit: LIST_LIMIT }),
    api<string[]>("teams", { sport, league }),
  ]);

  return (
    <>
      <p className="kicker">
        Matches{" "}
        <span className="sep">
          {league} {year}
        </span>
      </p>
      <h1 className="page">{q.team || "Every game"}</h1>
      <Filters
        leagues={leagues.map((item) => item.league)}
        league={league}
        years={yearsOf(leagueInfo)}
        year={year}
        teams={teams}
        team={q.team || ""}
        count={list.length}
      />
      <MatchList sport={sport} league={league} list={list} />
    </>
  );
}
