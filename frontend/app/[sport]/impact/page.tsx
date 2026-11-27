// Impact: who changes matches. Runs added above average, win chance added, wickets above
// average, and the single innings and spells that swung games most.

import type { Metadata } from "next";

import { Marked } from "@/components/Marked";
import { SliceNotes } from "@/components/SliceNotes";
import { SliceTable } from "@/components/SliceTable";
import { api } from "@/lib/api";
import { signed } from "@/lib/format";
import { leaguesOf } from "@/lib/meta";
import { type PageProps, readPage } from "@/lib/page";
import type { SliceAnswer, SliceQuery } from "@/lib/slices";
import { yearsOf } from "@/lib/types";

import { Filters } from "./Filters";

export const metadata: Metadata = { title: "Impact" };

const TOP_INNINGS = 15;
const INNINGS_BAT = ["runs", "balls", "sr", "fours", "sixes", "rae", "wpa"];
const INNINGS_BOWL = ["balls", "runs", "wkts", "econ", "waa", "rae", "wpa"];

function leadSentence(role: "bat" | "bowl", board: SliceAnswer) {
  const top = board.rows[0];
  if (!top) return null;
  const text =
    role === "bat"
      ? `${top.label} added ${signed(top.rae, 0)} runs above an average batter in the same spots.`
      : `${top.label} took ${signed(top.waa, 1)} wickets more than an average bowler on the same balls.`;
  return (
    <p className="standfirst">
      <Marked text={text} />
    </p>
  );
}

export default async function Impact(props: PageProps) {
  const { sport, q } = await readPage(props);
  const leagues = await leaguesOf(sport);
  const league = q.league || leagues[0].league;
  const info = leagues.find((item) => item.league === league) ?? leagues[0];
  const role = q.role === "bowl" ? "bowl" : "bat";
  const year = q.year || String(info.last);
  const years = year === "all" ? {} : { first: year, last: year };
  const base: SliceQuery = { role, league, phase: q.phase || undefined, ...years };
  const rank = role === "bat" ? "rae" : "waa";
  const [board, innings] = await Promise.all([
    api<SliceAnswer>("slice", { ...base, by: "player", sort: q.sort || rank }),
    api<SliceAnswer>("slice", { ...base, by: "innings", sort: "wpa" }),
  ]);
  innings.rows = innings.rows.slice(0, TOP_INNINGS);
  const what = role === "bat" ? "innings" : "spells";
  return (
    <>
      <p className="kicker">
        Impact{" "}
        <span className="sep">
          {league} {year === "all" ? "all years" : year}
        </span>
      </p>
      <h1 className="page">
        {role === "bat" ? "Batters who change games" : "Bowlers who change games"}
      </h1>
      {leadSentence(role, board)}
      <Filters
        role={role}
        leagues={leagues.map((item) => item.league)}
        league={league}
        years={yearsOf(info)}
        year={year}
        phase={q.phase ?? ""}
      />
      <h2 className="label">{board.title}</h2>
      <SliceTable sport={sport} answer={board} sort={q.sort || rank} />
      <h2 className="label">The {what} that swung matches most</h2>
      <p className="note">Ranked by win chance added in that one match.</p>
      <SliceTable
        sport={sport}
        answer={innings}
        sort="wpa"
        sortable={false}
        withTotal={false}
        only={role === "bat" ? INNINGS_BAT : INNINGS_BOWL}
      />
      <SliceNotes role={role} />
    </>
  );
}
