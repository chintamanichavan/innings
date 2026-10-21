// One ground's own page: how it plays, year by year, and its wildest games.

import type { Metadata } from "next";

import { LineChart } from "@/components/charts/LineChart";
import { Marked } from "@/components/Marked";
import { StoryCard } from "@/components/matches";
import { api } from "@/lib/api";
import { WORDS, day, num, pct } from "@/lib/format";
import { type PageProps, readPage } from "@/lib/page";
import { SPORTS } from "@/lib/sport";
import type { MatchSummary } from "@/lib/types";

const MIN_MATCHES_PER_YEAR = 3; // fewer than this and a year's average is noise
const CHART_HEIGHT = 220;

interface Ground {
  venue: string;
  n: number;
  first: string;
  last: string;
  avg1: number;
  avg2: number;
  first_win: number;
}

interface YearRow {
  year: number;
  n: number;
  avg1: number;
}

interface VenuePage {
  venue: Ground;
  by_year: YearRow[];
  classics: MatchSummary[];
}

type Props = PageProps<{ name: string }>;

export async function generateMetadata(props: Props): Promise<Metadata> {
  return { title: (await readPage(props)).args.name };
}

export default async function Venue(props: Props) {
  const { sport, args } = await readPage(props);
  const page = await api<VenuePage>("venue", { sport, name: args.name });
  const ground = page.venue;
  const first = WORDS[sport].first.toLowerCase();
  const second = WORDS[sport].second.toLowerCase();
  const lede =
    `${num(ground.n)} matches here, from ${day(ground.first)} to ${day(ground.last)}. ` +
    `The ${first} side wins ${pct(ground.first_win)} of them.`;
  const byYear = page.by_year
    .filter((year) => year.n >= MIN_MATCHES_PER_YEAR)
    .map((year) => ({ date: `${year.year}-07-01`, value: year.avg1 }));

  return (
    <>
      <p className="kicker">
        Venue <span className="sep">{SPORTS[sport]}</span>
      </p>
      <h1 className="page">{ground.venue}</h1>
      <p className="standfirst">
        <Marked text={lede} />
      </p>
      <div className="tiles">
        <div className="tile">
          <b>{num(ground.avg1, 1)}</b>
          <span>{first} runs per game</span>
        </div>
        <div className="tile">
          <b>{num(ground.avg2, 1)}</b>
          <span>{second} runs per game</span>
        </div>
        <div className="tile">
          <b>{pct(ground.first_win)}</b>
          <span>{first} side wins</span>
        </div>
      </div>
      <h2 className="label">Scoring by year</h2>
      <figure>
        <LineChart points={byYear} label="Runs per game" digits={1} maxHeight={CHART_HEIGHT} />
        <figcaption>
          {WORDS[sport].first} runs per game, each year with at least {MIN_MATCHES_PER_YEAR} matches.
        </figcaption>
      </figure>
      <h2 className="label">Wildest games here</h2>
      <div className="cols3">
        {page.classics.map((match) => (
          <StoryCard key={match.match_id} match={match} />
        ))}
      </div>
    </>
  );
}
