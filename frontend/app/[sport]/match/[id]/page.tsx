// One match, told as a story: the result, the win-chance chart, the moments that moved it,
// and who won it. The page is an ordered list of sections; add new ones to the list.

import type { Metadata } from "next";

import { Scorecard } from "@/components/scorecard/Scorecard";
import type { ScorecardData } from "@/components/scorecard/types";
import { api } from "@/lib/api";
import { type PageProps, readPage } from "@/lib/page";

import { loadMatch } from "./data";
import { Hero } from "./Hero";
import { Plays } from "./Plays";
import { Everyone, WhoDecidedIt } from "./PlayerLines";
import { Story } from "./Story";
import { WinFigure } from "./WinFigure";

type Props = PageProps<{ id: string }>;

export async function generateMetadata(props: Props): Promise<Metadata> {
  const { sport, args } = await readPage(props);
  const { story } = await loadMatch(sport, args.id);
  return {
    title: story.headline,
    description: story.paragraphs[0],
    openGraph: { title: story.headline, description: story.paragraphs[0], type: "article" },
  };
}

/** A match without a scorecard still gets its story. */
function loadScorecard(id: string): Promise<ScorecardData | null> {
  return api<ScorecardData>(`scorecard/${encodeURIComponent(id)}`).catch(() => null);
}

export default async function MatchPage(props: Props) {
  const { sport, args } = await readPage(props);
  const [loaded, scorecard] = await Promise.all([loadMatch(sport, args.id), loadScorecard(args.id)]);
  const { match, events, players, story, call } = loaded;
  return (
    <>
      <Hero sport={sport} match={match} story={story} call={call} />
      <WinFigure match={match} events={events} turning={story.turning.seq} />
      <Story sport={sport} matchId={match.match_id} paragraphs={story.paragraphs} />
      {scorecard && <Scorecard data={scorecard} />}
      <div className="cols2">
        <Plays match={match} events={events} />
        <WhoDecidedIt sport={sport} players={players} />
      </div>
      <Everyone sport={sport} players={players} />
    </>
  );
}
