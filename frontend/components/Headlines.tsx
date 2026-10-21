// A list of news headlines. Each one opens the publisher's own page in a new tab.

import { type Headline, timeAgo } from "@/lib/news";

interface HeadlineListProps {
  items: Headline[];
  columns?: boolean; // two side by side where there is room
}

export function HeadlineList({ items, columns = false }: HeadlineListProps) {
  const now = Date.now();
  return (
    <div className={columns ? "headlines two" : "headlines"}>
      {items.map((item) => (
        <a
          key={item.link}
          className="headline"
          href={item.link}
          target="_blank"
          rel="noopener noreferrer"
        >
          <p className="kicker quiet">
            {item.source}
            {item.published && <span className="sep">{timeAgo(item.published, now)}</span>}
          </p>
          <h3>{item.title}</h3>
          {item.summary && <p className="dek">{item.summary}</p>}
        </a>
      ))}
    </div>
  );
}
