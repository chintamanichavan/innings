// The live part of the page. It opens with what the server knew, then listens: the server
// pushes each new ball down one open connection, and the board redraws.

"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { num } from "@/lib/format";
import { type Figures, type LiveMatch, type News, type Snapshot, withRecords } from "@/lib/stream";

import { MatchCard } from "./MatchCard";
import { Pipeline } from "./Pipeline";

interface Live {
  matches: LiveMatch[];
  figures: Figures;
}

function useLive(initial: Snapshot): Live {
  const [live, setLive] = useState<Live>({ matches: initial.matches, figures: initial.figures });
  useEffect(() => {
    let source: EventSource | null = null;
    let left = false;

    const listen = (cursor: number) => {
      source = new EventSource(`/api/stream/events?after=${cursor}`);
      source.onmessage = (message) => {
        const news = JSON.parse(message.data as string) as News;
        if (news.reload) {
          source?.close();
          void startAgain();
          return;
        }
        setLive((now) => ({
          matches: withRecords(now.matches, news.records ?? []),
          figures: news.figures ?? now.figures,
        }));
      };
    };
    const startAgain = async () => {
      const fresh = await api<Snapshot>("stream");
      if (left) return;
      setLive({ matches: fresh.matches, figures: fresh.figures });
      listen(fresh.cursor);
    };

    listen(initial.cursor);
    return () => {
      left = true;
      source?.close();
    };
  }, [initial]);
  return live;
}

function Tiles({ figures }: { figures: Figures }) {
  const tiles: [value: string, text: string][] = [
    [num(figures.taken), "balls scored since the server started"],
    [num(figures.per_second, 1), "balls a second, right now"],
    [figures.delay_ms == null ? "–" : num(figures.delay_ms), "milliseconds from bowler to board"],
    [num(figures.matches), "matches on the board"],
  ];
  return (
    <div className="tiles">
      {tiles.map(([value, text]) => (
        <div className="tile" key={text}>
          <b>{value}</b>
          <span>{text}</span>
        </div>
      ))}
    </div>
  );
}

export function LiveBoard({ initial }: { initial: Snapshot }) {
  const { matches, figures } = useLive(initial);
  return (
    <>
      <Tiles figures={figures} />

      {matches.length ? (
        <div className="cols3 live-board">
          {matches.map((match) => (
            <MatchCard key={match.match_id} match={match} />
          ))}
        </div>
      ) : (
        <p className="note">
          {figures.connected ? "The next match is about to start." : "Waiting for Kafka to answer."}
        </p>
      )}

      <h2 className="label">The path of one ball</h2>
      <Pipeline figures={figures} />
    </>
  );
}
