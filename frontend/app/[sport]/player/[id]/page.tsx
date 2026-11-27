// One player: who they are in words, their skills, and the full numbers.

import type { Metadata } from "next";
import Link from "next/link";
import { cache } from "react";

import { Face } from "@/components/teams";
import { LineChart } from "@/components/charts/LineChart";
import { Marked } from "@/components/Marked";
import { ApiError, api } from "@/lib/api";
import { type PageProps, readPage } from "@/lib/page";
import { SliceTable } from "@/components/SliceTable";
import type { SliceAnswer, SliceQuery } from "@/lib/slices";
import { SPORTS, type Sport, link } from "@/lib/sport";

import { Actions } from "./Actions";
import { CareerSummary } from "./Career";
import { MostAlike } from "./Alike";
import { SkillProfile, roleName } from "./Sections";
import { GameLog, SeasonTables, SplitsSections } from "./Tables";
import type { Basics, Career, Extra, Role } from "./types";

const PREVIEW_SENTENCES = 2;

const load = cache(async (sport: Sport, id: string) => {
  const path = `${sport}/${encodeURIComponent(id)}`;
  const [basics, extra, career] = await Promise.all([
    api<Basics>(`player/${path}`),
    api<Extra>(`player-extra/${path}`),
    api<Career>(`career/${encodeURIComponent(id)}`),
  ]);
  return { basics, extra, career };
});

/** A batter against each bowling type, or a bowler against each batting hand. */
const matchupOf = (id: string, role: Role): SliceQuery =>
  role === "bat" ? { role, batter: id, by: "type" } : { role, bowler: id, by: "hand" };

export async function generateMetadata(props: PageProps<{ id: string }>): Promise<Metadata> {
  const { sport, args } = await readPage(props);
  try {
    const { basics, extra } = await load(sport, args.id);
    return { title: basics.name, description: extra.lede.slice(0, PREVIEW_SENTENCES).join(" ") };
  } catch (error) {
    if (error instanceof ApiError) return {};
    throw error;
  }
}

export default async function Player(props: PageProps<{ id: string }>) {
  const { sport, args } = await readPage(props);
  const { basics, extra, career } = await load(sport, args.id);
  const matchup = matchupOf(args.id, extra.role);
  const matchups = await api<SliceAnswer>("slice", matchup);
  const roles = (Object.keys(basics.roles) as Role[])
    .map((role) => roleName(sport, role))
    .join(" and ");

  return (
    <>
      <article>
        <p className="kicker">
          {SPORTS[sport]} <span className="sep">{roles}</span>
        </p>
        <div className="row title">
          <Face name={basics.name} size="xl" />
          <h1>{basics.name}</h1>
        </div>
        <Actions sport={sport} id={args.id} name={basics.name} />
        <div className="prose spaced">
          {extra.lede.map((text) => (
            <p key={text}>
              <Marked text={text} />
            </p>
          ))}
        </div>
      </article>
      <CareerSummary sport={sport} career={career} bowler={extra.role === "bowl"} />
      <SkillProfile sport={sport} profiles={extra.profiles} />
      <MostAlike sport={sport} id={args.id} alike={extra.alike} />
      <h2 className="label">Matchups</h2>
      <SliceTable sport={sport} answer={matchups} sort="" sortable={false} />
      <p className="note">
        <Link href={link(sport, "matchups", "", { ...matchup })}>
          Every matchup: by bowler, phase, ground and year
        </Link>
      </p>
      <h2 className="label">Career value</h2>
      <figure>
        <LineChart points={extra.series} label="Runs above average so far" reference={0} />
        <figcaption>
          Running total of runs added above an average player (
          {roleName(sport, extra.role).toLowerCase()}). A rising line is a good spell. The dashed line
          is average.
        </figcaption>
      </figure>
      {/* The long tables are for digging. They stay folded until asked for. */}
      <details className="more">
        <summary>Season by season</summary>
        <SeasonTables sport={sport} roles={basics.roles} />
      </details>
      <details className="more">
        <summary>Splits: by innings, phase and venue</summary>
        <SplitsSections sport={sport} roles={basics.roles} splits={extra.splits} />
      </details>
      <details className="more">
        <summary>Every game, with runs added</summary>
        <GameLog sport={sport} log={extra.log} />
      </details>
    </>
  );
}
