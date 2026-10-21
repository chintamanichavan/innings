// A plain list of every section. On a phone this is the "More" tab.

import type { Metadata } from "next";
import Link from "next/link";

import { type PageProps, readPage } from "@/lib/page";
import { SPORTS, link } from "@/lib/sport";

export const metadata: Metadata = { title: "Sections" };

const SECTIONS: [page: string, title: string, blurb: string][] = [
  ["news", "News", "The newest headlines from five publishers."],
  ["lab", "The lab", "A neural network learns cricket. Watch it, ask it, test it."],
  ["stream", "The stream", "A season played 100,000 times, through Kafka into a data lake."],
  ["puzzles", "Puzzles", "Who am I, higher or lower, you against the model."],
  ["following", "Following", "Your teams and players."],
  ["players", "Players", "Leaderboards for every league and year."],
  ["teams", "Teams", "Power rankings and a matchup forecast."],
  ["matches", "Matches", "Every game, with its story."],
  ["records", "Records", "The wildest games, comebacks and plays."],
  ["venues", "Venues", "Where the runs are."],
  ["compare", "Compare", "Any two cricketers, side by side."],
  ["methods", "How it works", "The models, in plain words."],
];

export default async function Sections(props: PageProps) {
  const { sport } = await readPage(props);
  return (
    <>
      <p className="kicker">Sections</p>
      <h1 className="page">{SPORTS[sport]}</h1>
      <div className="rows narrow spaced">
        {SECTIONS.map(([page, title, blurb]) => (
          <Link key={page} className="rowlink two" href={link(sport, page)}>
            <span>
              <b className="section-name">{title}</b>
              <small>{blurb}</small>
            </span>
            <span aria-hidden="true">→</span>
          </Link>
        ))}
      </div>
    </>
  );
}
