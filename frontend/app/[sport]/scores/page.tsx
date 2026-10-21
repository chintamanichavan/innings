// The scores page: matches being played now, then the latest finished ones.

import type { Metadata } from "next";

import { LiveScores } from "@/components/LiveScores";
import { MatchTable } from "@/components/matches";
import { api } from "@/lib/api";
import { type PageProps, readPage } from "@/lib/page";

import type { Home } from "../types";

export const metadata: Metadata = { title: "Latest cricket" };

export default async function Scores(props: PageProps) {
  const { sport } = await readPage(props);
  const home = await api<Home>("home", { sport });
  return (
    <>
      <p className="kicker">Scores</p>
      <h1 className="page">Latest cricket</h1>
      <p className="standfirst">
        Live scores come from a free feed, so they show the score and nothing finer. Full scorecards and
        stories arrive a day or so after a match ends.
      </p>
      <h2 className="label">Live now</h2>
      <LiveScores grid />
      <h2 className="label">Latest results</h2>
      <MatchTable sport={sport} matches={home.recent} />
      <p className="note">Franchise leagues and matches between full member nations.</p>
    </>
  );
}
