// The leaderboard: every player in a league and year, sortable by any column.

import type { Metadata } from "next";

import { Marked } from "@/components/Marked";
import { api } from "@/lib/api";
import { WORDS, signed } from "@/lib/format";
import { leaguesOf } from "@/lib/meta";
import { type PageProps, readPage } from "@/lib/page";
import { yearsOf } from "@/lib/types";

import { Board } from "./Board";
import { Filters } from "./Filters";
import type { Leaders } from "./types";

export async function generateMetadata(props: PageProps): Promise<Metadata> {
  const { sport, q } = await readPage(props);
  return { title: WORDS[sport][q.role || "bat"] };
}

function leaderSentence(board: Leaders, ascending: boolean) {
  const top = board.rows[0];
  if (!top || board.sort !== "rae" || ascending) return null;
  const text = `${top.name} leads: ${signed(top.rae, 0)} runs against an average player in the same spots.`;
  return (
    <p className="standfirst">
      <Marked text={text} />
    </p>
  );
}

export default async function Players(props: PageProps) {
  const { sport, q } = await readPage(props);
  const leagues = await leaguesOf(sport);
  const league = q.league || leagues[0].league;
  const leagueInfo = leagues.find((item) => item.league === league) ?? leagues[0];
  const role = q.role || "bat";
  const year = q.year === "all" ? "" : q.year || String(leagueInfo.last);
  const ascending = q.asc === "true";
  const data = await api<Leaders>("leaders", {
    sport,
    role,
    league,
    year,
    min_opps: q.min,
    sort: q.sort,
    asc: q.asc,
  });

  return (
    <>
      <p className="kicker">
        Players{" "}
        <span className="sep">
          {league} {year || "all years"}
        </span>
      </p>
      <h1 className="page">{WORDS[sport][role]}</h1>
      {leaderSentence(data, ascending)}
      <Filters
        sport={sport}
        role={role}
        leagues={leagues.map((item) => item.league)}
        league={league}
        years={yearsOf(leagueInfo)}
        year={year}
        minimum={data.min_opps}
        minimumOf="balls"
      />
      <Board sport={sport} league={league} data={data} ascending={ascending} />
      <p className="note">
        <b>RAE</b> is runs added above an average player. <b>WPA</b> is wins added. <b>Clutch</b> is
        wins added beyond what those runs are usually worth. Tap a column to sort.
      </p>
    </>
  );
}
