// The news page: the newest cricket headlines from several publishers, linking out to each.

import type { Metadata } from "next";

import { Pills } from "@/components/controls";
import { HeadlineList } from "@/components/Headlines";
import { api } from "@/lib/api";
import type { News } from "@/lib/news";
import { type PageProps, readPage } from "@/lib/page";
import { link } from "@/lib/sport";

export const metadata: Metadata = {
  title: "Cricket news",
  description: "The newest cricket headlines from ESPNcricinfo, the BBC, the Guardian, NDTV and Sky.",
};

const HEADLINES = 100;
const EVERYONE = "";

export default async function NewsPage(props: PageProps) {
  const { sport, q } = await readPage(props);
  const chosen = q.source ?? EVERYONE;
  const news = await api<News>("news", { limit: HEADLINES, source: chosen });
  const answering = news.sources.filter((source) => source.ok);
  const silent = news.sources.filter((source) => !source.ok).map((source) => source.name);
  const pills: [string, string, string][] = [
    [EVERYONE, "All", link(sport, "news")],
    ...answering.map((source): [string, string, string] => [
      source.name,
      source.name,
      link(sport, "news", "", { source: source.name }),
    ]),
  ];

  return (
    <>
      <p className="kicker">News</p>
      <h1 className="page">Cricket news</h1>
      <p className="standfirst">
        The newest headlines, straight from the publishers. Each one opens the full story on their own
        site.
      </p>
      <Pills items={pills} current={chosen} />
      {news.items.length ? (
        <HeadlineList items={news.items} />
      ) : (
        <p className="empty">No headlines could be read just now. Try again in a few minutes.</p>
      )}
      {silent.length > 0 && <p className="note">Not answering just now: {silent.join(", ")}.</p>}
      <p className="note">
        Headlines and summaries come from each publisher&apos;s public RSS feed. The stories are theirs.
      </p>
    </>
  );
}
