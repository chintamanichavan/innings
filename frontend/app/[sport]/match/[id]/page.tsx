// One match, told as a story: the result, the win-chance chart, the moments that moved it,
// and who won it. The page is an ordered list of sections; add new ones to the list.

import type { Metadata } from "next";

import { MatchGraphs } from "@/components/scorecard/MatchGraphs";
import { Scorecard } from "@/components/scorecard/Scorecard";
import { ScoreSummary } from "@/components/scorecard/Summary";
import type { ScorecardData } from "@/components/scorecard/types";
import { api } from "@/lib/api";
import { type PageProps, readPage } from "@/lib/page";

import { Commentary } from "./Commentary";
import { loadMatch } from "./data";
import { Hero } from "./Hero";
import { Plays } from "./Plays";
import { Everyone, WhoDecidedIt } from "./PlayerLines";
import { Story } from "./Story";
import { Tabs, tabOf } from "./Tabs";
import type { CommentaryData } from "./types";
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

function loadCommentary(id: string): Promise<CommentaryData | null> {
  return api<CommentaryData>(`commentary/${encodeURIComponent(id)}`).catch(() => null);
}

const NO_CARD = <p className="note">There is no ball-by-ball record of this match.</p>;

export default async function MatchPage(props: Props) {
  const { sport, args, q } = await readPage(props);
  const tab = tabOf(q.tab);
  const [loaded, scorecard, commentary] = await Promise.all([
    loadMatch(sport, args.id),
    tab === "commentary" ? null : loadScorecard(args.id),
    tab === "commentary" ? loadCommentary(args.id) : null,
  ]);
  const { match, events, players, story, call } = loaded;
  return (
    <>
      <Hero sport={sport} match={match} story={story} call={call} star={players[0] ?? null} />
      <Tabs sport={sport} id={args.id} on={tab} />

      {tab === "summary" && (
        <>
          {scorecard && <ScoreSummary data={scorecard} />}
          <h2 className="label">Win probability</h2>
          <WinFigure match={match} events={events} turning={story.turning.seq} />
          <Story sport={sport} matchId={match.match_id} paragraphs={story.paragraphs} />
          <div className="cols2">
            <Plays match={match} events={events} />
            <WhoDecidedIt sport={sport} players={players} />
          </div>
        </>
      )}

      {tab === "scorecard" && (
        <>
          {scorecard ? <Scorecard data={scorecard} /> : NO_CARD}
          <Everyone sport={sport} players={players} />
        </>
      )}

      {tab === "commentary" && (commentary ? <Commentary data={commentary} /> : NO_CARD)}

      {tab === "graphs" && (
        <>
          <h2 className="label">Win probability</h2>
          <WinFigure match={match} events={events} turning={story.turning.seq} />
          {scorecard ? <MatchGraphs data={scorecard} /> : NO_CARD}
        </>
      )}
    </>
  );
}
