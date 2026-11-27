// Ask: a cricket question in plain words, answered from every ball. The question lives in
// the address, so an answer is a link to share.

import type { Metadata } from "next";
import Link from "next/link";

import { SliceNotes } from "@/components/SliceNotes";
import { SliceTable } from "@/components/SliceTable";
import { api } from "@/lib/api";
import { type PageProps, readPage } from "@/lib/page";
import type { SliceAnswer } from "@/lib/slices";
import { type Sport, link } from "@/lib/sport";

interface Reply {
  question: string;
  understood: { text: string; means: string }[];
  unknown: string[];
  sort: string;
  answer: SliceAnswer | null;
  examples: string[];
}

export async function generateMetadata(props: PageProps): Promise<Metadata> {
  const { q } = await readPage(props);
  return { title: q.q ? `${q.q} · Ask` : "Ask" };
}

function Examples({ sport, examples }: { sport: Sport; examples: string[] }) {
  return (
    <div className="pills">
      {examples.map((example) => (
        <Link key={example} href={link(sport, "ask", "", { q: example })}>
          {example}
        </Link>
      ))}
    </div>
  );
}

function HowRead({ reply }: { reply: Reply }) {
  return (
    <div className="chips">
      {reply.understood.map((part) => (
        <span key={part.text} className="chip" title={`"${part.text}"`}>
          {part.means}
        </span>
      ))}
      {reply.unknown.length > 0 && (
        <span className="note">
          Not understood: {reply.unknown.map((word) => `"${word}"`).join(", ")}
        </span>
      )}
    </div>
  );
}

export default async function Ask(props: PageProps) {
  const { sport, q } = await readPage(props);
  const question = q.q ?? "";
  const reply = await api<Reply>("ask", { q: question, sort: q.sort });
  const answer = reply.answer;
  return (
    <>
      <p className="kicker">Ask</p>
      <h1 className="page">{answer ? answer.title : "Ask a cricket question"}</h1>
      <form className="ask" action={link(sport, "ask")} method="get">
        <input
          name="q"
          type="search"
          defaultValue={question}
          placeholder="Kohli vs leg spin since 2020"
          aria-label="Your question"
          autoComplete="off"
        />
        <button className="btn" type="submit">
          Ask
        </button>
      </form>
      {question && <HowRead reply={reply} />}
      {answer ? (
        <>
          <SliceTable sport={sport} answer={answer} sort={reply.sort} />
          <p className="note">
            <Link href={link(sport, "matchups", "", { ...answer.slice })}>
              Change the filters by hand
            </Link>
          </p>
          <SliceNotes role={answer.slice.role === "bowl" ? "bowl" : "bat"} />
        </>
      ) : (
        question && <p className="empty">No player, team, league or phase found in that question.</p>
      )}
      <h2 className="label">Try</h2>
      <Examples sport={sport} examples={reply.examples} />
      <p className="note">
        Name players, teams, grounds, leagues (IPL, BBL, T20I…), formats, phases (powerplay, middle,
        death), bowling types (leg spin, left-arm pace…), left or right handers, years (2024, since
        2020, 2018-2022), chasing or batting first. Add &ldquo;by year&rdquo;, &ldquo;by ground&rdquo;
        or &ldquo;best&rdquo; to change the table.
      </p>
    </>
  );
}
