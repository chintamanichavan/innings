// Matchups: a batter against bowlers, or a bowler against batters, cut any way.

import type { Metadata } from "next";
import { cache } from "react";

import { SliceNotes } from "@/components/SliceNotes";
import { SliceTable } from "@/components/SliceTable";
import { api } from "@/lib/api";
import { leaguesOf } from "@/lib/meta";
import { type PageProps, readPage } from "@/lib/page";
import { type SliceAnswer, type SliceQuery, roleOf, sliceOf, sliceParams } from "@/lib/slices";

import { Filters } from "./Filters";

/** With no split chosen: two players go year by year; one player goes by the other side's style. */
function withDefaults(query: SliceQuery): SliceQuery {
  const role = roleOf(query);
  const by = query.by ?? (query.batter && query.bowler ? "year" : role === "bat" ? "type" : "hand");
  return { ...query, role, by: by === "none" ? "" : by };
}

// Keyed by the address's query as text, so the title and the page share one request.
const loadQuery = cache(async (text: string) => {
  const q = JSON.parse(text) as Record<string, string>;
  const slice = withDefaults(sliceOf(q));
  return { slice, answer: await api<SliceAnswer>("slice", sliceParams(slice, q.sort)) };
});
const load = (q: Record<string, string>) => loadQuery(JSON.stringify(q));

export async function generateMetadata(props: PageProps): Promise<Metadata> {
  const { q } = await readPage(props);
  if (!q.batter && !q.bowler) return { title: "Matchups" };
  return { title: (await load(q)).answer.title };
}

export default async function Matchups(props: PageProps) {
  const { sport, q } = await readPage(props);
  const [{ slice, answer }, leagues] = await Promise.all([load(q), leaguesOf(sport)]);
  const last = Math.max(...leagues.map((league) => league.last));
  const first = Math.min(...leagues.map((league) => league.first));
  const years = Array.from({ length: last - first + 1 }, (_, index) => last - index);
  return (
    <>
      <p className="kicker">Matchups</p>
      <h1 className="page">{answer.title}</h1>
      <p className="standfirst">
        Pick a batter, a bowler or both. Split by bowling type, batting hand, phase, ground or year.
      </p>
      <Filters
        slice={slice}
        role={roleOf(slice)}
        names={{ batter: answer.names.batter ?? undefined, bowler: answer.names.bowler ?? undefined }}
        leagues={leagues.map((league) => league.league)}
        years={years}
      />
      <SliceTable sport={sport} answer={answer} sort={q.sort ?? ""} />
      <SliceNotes role={roleOf(slice)} />
    </>
  );
}
