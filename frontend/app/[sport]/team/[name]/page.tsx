// One team: where it stands, how its strength has moved, its best players and best wins.

import type { Metadata } from "next";

import { LineChart } from "@/components/charts/LineChart";
import { Marked } from "@/components/Marked";
import { MatchTable, StoryCard } from "@/components/matches";
import { Crest } from "@/components/teams";
import { api } from "@/lib/api";
import { WORDS } from "@/lib/format";
import { leaguesOf } from "@/lib/meta";
import { type PageProps, readPage } from "@/lib/page";
import { SPORTS } from "@/lib/sport";

import { Actions } from "./Actions";
import { PointsTable, Squad } from "./SeasonParts";
import { Leaders, SeasonsTable } from "./Sections";
import type { TeamPage } from "./types";

const CLASSICS_SHOWN = 2;
const AVERAGE_RATING = 1500;

export async function generateMetadata(props: PageProps<{ name: string }>): Promise<Metadata> {
  const { args } = await readPage(props);
  return {
    title: args.name,
    description: `${args.name}: rating history, seasons, best players and greatest wins.`,
  };
}

export default async function Team(props: PageProps<{ name: string }>) {
  const { sport, args, q } = await readPage(props);
  const pool = q.pool || (await leaguesOf(sport))[0].league;
  const page = await api<TeamPage>("team", { sport, pool, team: args.name });
  const words = WORDS[sport];
  const history = page.elo.map((point) => ({ date: point.date, value: point.elo }));

  return (
    <>
      <article>
        <p className="kicker">
          {SPORTS[sport]} <span className="sep">{pool}</span>
        </p>
        <div className="row title">
          <Crest team={page.team} size="xl" />
          <h1>{page.team}</h1>
        </div>
        <Actions sport={sport} team={args.name} pool={pool} title={page.team} />
        <div className="prose spaced">
          {page.lede.map((text) => (
            <p key={text}>
              <Marked text={text} />
            </p>
          ))}
        </div>
      </article>
      <div className={page.table ? "cols2 season-pair" : ""}>
        {page.table && (
          <section>
            <h2 className="label">
              {pool} {page.year}: points table
            </h2>
            <PointsTable sport={sport} pool={pool} team={page.team} rows={page.table} />
            <p className="note">League stage. The line marks the four playoff places.</p>
          </section>
        )}
        <section>
          <h2 className="label">Squad, {page.year}</h2>
          <Squad sport={sport} players={page.squad} />
          <p className="note">
            Roles are read from what each player did. m matches, r runs, w wickets.
          </p>
        </section>
      </div>
      <h2 className="label">Strength over time</h2>
      <figure>
        <LineChart points={history} label="Rating" reference={AVERAGE_RATING} />
        <figcaption>
          Our rating after every game. The dashed line at 1,500 is an average side.
        </figcaption>
      </figure>
      <div className="cols2">
        <section>
          <h2 className="label">Best of {page.year}</h2>
          <div className="panel pair">
            <Leaders sport={sport} title={words.bat} players={page.best.bat} />
            <Leaders sport={sport} title={words.bowl} players={page.best.bowl} />
          </div>
          <p className="note">Runs added above an average player.</p>
        </section>
        <section>
          <h2 className="label">Greatest wins</h2>
          <div className="stack">
            {page.classics.slice(0, CLASSICS_SHOWN).map((match) => (
              <StoryCard key={match.match_id} match={match} />
            ))}
          </div>
        </section>
      </div>
      <SeasonsTable sport={sport} team={page.team} seasons={page.seasons} />
      <h2 className="label">Latest games</h2>
      <MatchTable sport={sport} matches={page.games} />
    </>
  );
}
