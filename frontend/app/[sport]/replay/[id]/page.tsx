// Watch it ball by ball: one match, one ball at a time.

import type { Metadata } from "next";

import { cache } from "react";

import { api } from "@/lib/api";
import { day } from "@/lib/format";
import { type PageProps, readPage } from "@/lib/page";
import type { Sport } from "@/lib/sport";

import { Replay } from "./Replay";
import type { ReplayPage } from "./types";

type Props = PageProps<{ id: string }>;

// Cached, so the page and its title share one request.
const load = cache((sport: Sport, id: string) =>
  api<ReplayPage>(`match/${sport}/${encodeURIComponent(id)}`),
);

export async function generateMetadata(props: Props): Promise<Metadata> {
  const { sport, args } = await readPage(props);
  const { match } = await load(sport, args.id);
  return { title: `${match.team1} v ${match.team2}` };
}

export default async function ReplayRoute(props: Props) {
  const { sport, args } = await readPage(props);
  const { match, events, story } = await load(sport, args.id);
  return (
    <>
      <p className="kicker">
        Ball by ball{" "}
        <span className="sep">
          {match.league} · {day(match.date)}
        </span>
      </p>
      <h1 className="page">
        {match.team1} v {match.team2}
      </h1>
      <p className="standfirst">
        One ball at a time. The line shows {match.team1}&apos;s chance of winning.
      </p>
      <Replay sport={sport} match={match} events={events} firstParagraph={story.paragraphs[0]} />
    </>
  );
}
