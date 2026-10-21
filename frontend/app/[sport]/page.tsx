// The front page: the reader's teams, the top story, today's scores, and things worth a look.

import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { WinChart } from "@/components/charts/WinChart";
import { HeadlineList } from "@/components/Headlines";
import { LiveScores } from "@/components/LiveScores";
import { Marked } from "@/components/Marked";
import { MatchTable, Media, Scorebox, StoryCard } from "@/components/matches";
import { api } from "@/lib/api";
import { day, num, pct, yearOf } from "@/lib/format";
import type { News } from "@/lib/news";
import { type PageProps, readPage } from "@/lib/page";
import { SPORTS, type Sport, link } from "@/lib/sport";
import type { MatchSummary } from "@/lib/types";

import { FollowedPlayerLinks, PuzzlePanel, YourTeams } from "./DeviceParts";
import { FormGuide } from "./FormGuide";
import type { Home, Lead } from "./types";

export const metadata: Metadata = { title: "Front page" };

const LATEST_SCORES = 5;
const LIVE_ON_FRONT = 4;
const NEWS_ON_FRONT = 6;
const LEAD_PARAGRAPHS = 2;
const NO_SCORE = { league: "", score1: null, score2: null, winner: null }; // a picture of two teams only

function DateLine({ sport }: { sport: Sport }) {
  const date = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  return (
    <h2 className="today">
      {SPORTS[sport]}
      <span>{date}</span>
    </h2>
  );
}

function TopStory({ sport, lead }: { sport: Sport; lead: Lead | null }) {
  if (!lead) return <p className="empty">No matches yet.</p>;
  const { match, story } = lead;
  const href = link(sport, "match", match.match_id);
  return (
    <div className="card hero">
      <Link href={href}>
        <Media match={match} wide tag="Game of the week" />
      </Link>
      <div className="body">
        <p className="kicker">
          {match.league} <span className="sep">{day(match.date)}</span>
        </p>
        <Link href={href}>
          <h1>{story.headline}</h1>
        </Link>
        <p className="standfirst">
          <Marked text={story.standfirst} />
        </p>
        <WinChart
          events={lead.events}
          team1={match.team1}
          team2={match.team2}
          turning={story.turning.seq}
          compact
        />
        <p className="note chart-note">
          {match.team1}&apos;s chance of winning, from first ball to last.
        </p>
        <div className="prose small">
          {story.paragraphs.slice(0, LEAD_PARAGRAPHS).map((text) => (
            <p key={text}>
              <Marked text={text} />
            </p>
          ))}
        </div>
        <Link className="btn sm" href={href}>
          Read the full story
        </Link>
      </div>
    </div>
  );
}

function LivePanel({ sport }: { sport: Sport }) {
  return (
    <section className="panel">
      <p className="kicker">Live now</p>
      <LiveScores limit={LIVE_ON_FRONT} />
      <p className="note">
        <Link className="u" href={link(sport, "scores")}>
          All live scores
        </Link>
      </p>
    </section>
  );
}

/**
 * The newest headlines, under the top story. Feeds can be slow, so this arrives after the
 * rest of the page.
 */
async function NewsSection({ sport }: { sport: Sport }) {
  const news = await api<News>("news", { limit: NEWS_ON_FRONT }).catch(() => null);
  if (!news?.items.length) return null;
  return (
    <section>
      <h2 className="label">In the news</h2>
      <div className="panel">
        <HeadlineList items={news.items} columns />
        <p className="note">
          <Link className="u" href={link(sport, "news")}>
            All the news
          </Link>
        </p>
      </div>
    </section>
  );
}

function ScoresPanel({ sport, recent }: { sport: Sport; recent: MatchSummary[] }) {
  return (
    <section className="panel">
      <p className="kicker">Latest scores</p>
      <div>
        {recent.slice(0, LATEST_SCORES).map((match) => (
          <Link key={match.match_id} className="score-link" href={link(sport, "match", match.match_id)}>
            <Scorebox match={match} />
            <div className="meta">
              {day(match.date)} · {match.league}
            </div>
          </Link>
        ))}
      </div>
      <p className="note">
        <Link className="u" href={link(sport, "scores")}>
          All scores
        </Link>
      </p>
    </section>
  );
}

function ForecasterPanel({ sport, forecast }: { sport: Sport; forecast: Home["forecast"] }) {
  const share = num((100 * forecast.right) / forecast.n, 1);
  return (
    <div className="panel">
      <p className="kicker quiet">The forecaster</p>
      <h3>Every call, on the record</h3>
      <p>
        <Marked text={`${num(forecast.n)} calls scored. ${share}% right.`} />
      </p>
      <Link className="btn alt sm" href={link(sport, "forecasts")}>
        See the record
      </Link>
    </div>
  );
}

function PlayOfTheDay({ sport, play }: { sport: Sport; play: Home["top_play"] }) {
  return (
    <Link className="card" href={link(sport, "match", play.match_id)}>
      <Media match={{ ...NO_SCORE, sport, team1: play.team1, team2: play.team2 }} />
      <div className="body">
        <p className="kicker">Play of the day</p>
        <h3>{play.text}</h3>
        <p className="dek">
          {play.team1} went from {pct(play.wp1)} to {pct(play.wp1_post)} · {day(play.date)}
        </p>
      </div>
    </Link>
  );
}

function Archive({ sport, home }: { sport: Sport; home: Home }) {
  const anniversary = home.on_this_day[0];
  return (
    <>
      <h2 className="label">From the archive</h2>
      <div className="cols3">
        {home.classic && <StoryCard match={home.classic} label="Classic of the day" />}
        {anniversary && (
          <StoryCard match={anniversary} label={`On this day, ${yearOf(anniversary.date)}`} />
        )}
        <PlayOfTheDay sport={sport} play={home.top_play} />
      </div>
    </>
  );
}

export default async function Front(props: PageProps) {
  const { sport, q } = await readPage(props);
  const home = await api<Home>("home", { sport, league: q.hot });

  return (
    <>
      <DateLine sport={sport} />
      <YourTeams sport={sport} />
      <div className="front">
        <div>
          <article>
            <TopStory sport={sport} lead={home.lead} />
          </article>
          <Suspense>
            <NewsSection sport={sport} />
          </Suspense>
        </div>
        <aside className="rail">
          <LivePanel sport={sport} />
          <ScoresPanel sport={sport} recent={home.recent} />
          <ForecasterPanel sport={sport} forecast={home.forecast} />
          <PuzzlePanel sport={sport} />
        </aside>
      </div>
      <FormGuide sport={sport} home={home} />
      <Archive sport={sport} home={home} />
      <FollowedPlayerLinks sport={sport} />
      <h2 className="label">Latest results</h2>
      <MatchTable sport={sport} matches={home.recent} />
      <p className="note">History runs to {day(home.latest)} and refreshes twice a day.</p>
    </>
  );
}
