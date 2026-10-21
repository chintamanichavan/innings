// Venues: every ground, with its average scores.

import type { Metadata } from "next";
import Link from "next/link";

import { api } from "@/lib/api";
import { WORDS, num, pct } from "@/lib/format";
import { type PageProps, readPage } from "@/lib/page";
import { link } from "@/lib/sport";

export const metadata: Metadata = { title: "Where the runs are" };

interface VenueRow {
  venue: string;
  league: string;
  n: number;
  avg1: number;
  avg2: number;
  first_win: number;
}

export default async function Venues(props: PageProps) {
  const { sport } = await readPage(props);
  const list = await api<VenueRow[]>("venues", { sport });
  const words = WORDS[sport];
  return (
    <>
      <p className="kicker">Venues</p>
      <h1 className="page">Where the runs are</h1>
      <p className="standfirst">And where batting first pays.</p>
      <div className="scroll spaced">
        <table>
          <thead>
            <tr>
              <th className="l">Venue</th>
              <th className="l">Mostly</th>
              <th>Matches</th>
              <th>{words.first} runs</th>
              <th>{words.second} runs</th>
              <th>{words.first} wins</th>
            </tr>
          </thead>
          <tbody>
            {list.map((venue) => (
              <tr key={`${venue.venue}-${venue.league}`}>
                <td className="l">
                  <Link className="u" href={link(sport, "venue", venue.venue)}>
                    {venue.venue}
                  </Link>
                </td>
                <td className="l dim">{venue.league}</td>
                <td>{num(venue.n)}</td>
                <td>{num(venue.avg1, 1)}</td>
                <td>{num(venue.avg2, 1)}</td>
                <td>{pct(venue.first_win)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
