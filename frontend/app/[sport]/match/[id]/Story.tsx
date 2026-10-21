// The written story of the match, with a link to watch it ball by ball.

import Link from "next/link";

import { Marked } from "@/components/Marked";
import { type Sport, link } from "@/lib/sport";

interface StoryProps {
  sport: Sport;
  matchId: string;
  paragraphs: string[];
}

export function Story({ sport, matchId, paragraphs }: StoryProps) {
  return (
    <article className="article">
      <div className="prose lead">
        {paragraphs.map((text, index) => (
          <p key={index}>
            <Marked text={text} />
          </p>
        ))}
      </div>
      <div className="panel">
        <p className="kicker quiet">The replay</p>
        <Link className="btn alt sm" href={link(sport, "replay", matchId)}>
          Watch it ball by ball
        </Link>
      </div>
    </article>
  );
}
