// Power rankings for a league, a matchup forecast, and how well the forecast has done.

import type { Metadata } from "next";

import { Marked } from "@/components/Marked";
import { api } from "@/lib/api";
import { WORDS, num } from "@/lib/format";
import { leaguesOf } from "@/lib/meta";
import { type PageProps, readPage } from "@/lib/page";

import { Result, TrackRecord } from "./Forecast";
import { Matchup } from "./Matchup";
import { PoolFilter } from "./PoolFilter";
import { ColumnsNote, MembersNote, RankingsTable } from "./Rankings";
import type { Evaluation, Ratings } from "./types";

export const metadata: Metadata = { title: "Power rankings" };

const AVERAGE_RATING = "1,500";

export default async function Teams(props: PageProps) {
  const { sport, q } = await readPage(props);
  const leagues = await leaguesOf(sport);
  const pools = leagues.map((league) => league.league);
  const pool = q.pool || pools[0];
  const [ratings, evaluation] = await Promise.all([
    api<Ratings>("ratings", { sport, pool, everyone: q.all }),
    api<Evaluation>("eval", { sport }),
  ]);
  const names = ratings.rows.map((row) => row.team);
  const a = q.a || names[0];
  const b = q.b || names[1];
  const best = ratings.rows[0];

  return (
    <>
      <p className="kicker">
        Teams <span className="sep">{pool}</span>
      </p>
      <h1 className="page">Power rankings</h1>
      <p className="standfirst">
        {best && (
          <Marked
            text={
              `${best.team} are the strongest side right now, rated ${num(best.elo)}. ` +
              `An average side is ${AVERAGE_RATING}.`
            }
          />
        )}
      </p>
      <PoolFilter pools={pools} pool={pool} />
      <div className="cols2">
        <section>
          <MembersNote sport={sport} ratings={ratings} q={q} />
          <RankingsTable sport={sport} pool={pool} rows={ratings.rows} />
          <ColumnsNote pool={pool} />
        </section>
        <section>
          <Matchup teams={names} a={a} b={b}>
            <Result sport={sport} pool={pool} a={a} b={b} />
          </Matchup>
          <TrackRecord evaluation={evaluation} side={WORDS[sport].first.toLowerCase()} />
        </section>
      </div>
    </>
  );
}
