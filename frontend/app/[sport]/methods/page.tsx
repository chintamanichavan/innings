// How it works: the method in plain words, the tables behind it, the data, the limits.

import type { Metadata } from "next";

import { api } from "@/lib/api";
import { day, num } from "@/lib/format";
import { getMeta, leaguesOf } from "@/lib/meta";
import { type PageProps, readPage } from "@/lib/page";

import { CricketModelSection } from "./Models";
import type { CricketModel } from "./types";

export const metadata: Metadata = { title: "One method, built on cricket" };

const WOMENS = "(W)";

function Intro() {
  return (
    <>
      <p className="kicker">How it works</p>
      <h1 className="page">One method, built on cricket</h1>
      <article className="article">
        <div className="prose spaced">
          <p>
            One player delivers a ball, and one player tries to hit it. So one method can measure every
            ball.
          </p>
          <p>
            <b>Describe the state.</b> Limited-overs cricket: balls left and wickets down. Test cricket:
            wickets down, the lead, and how much of the match is gone.
          </p>
          <p>
            <b>Value the state.</b> From history, how many more runs does an average side score from
            here? And how often does it win?
          </p>
          <p>
            <b>Credit the change.</b> Runs above expected (RAE) is runs scored, plus the value after,
            minus the value before. Win probability added (WPA) is the win chance after minus the win
            chance before. The batter gets it. The bowler gets the opposite.
          </p>
          <p>
            <b>Go further.</b> Clutch is the win chance a player added beyond what those runs are
            usually worth. Thrill is how far the win chance travelled in a game. A profile ranks five
            skills against every qualified player.
          </p>
        </div>
      </article>
    </>
  );
}

async function DataTable() {
  const { leagues } = await getMeta();
  return (
    <>
      <h2 className="label">The data</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th className="l">League</th>
              <th>Years</th>
              <th>Matches</th>
              <th>Latest</th>
            </tr>
          </thead>
          <tbody>
            {leagues.map((league) => (
              <tr key={`${league.sport}-${league.league}`}>
                <td className="l">{league.league}</td>
                <td>
                  {league.first}–{league.last}
                </td>
                <td>{num(league.matches)}</td>
                <td>{day(league.latest)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Limits() {
  return (
    <>
      <h2 className="label">Known limits</h2>
      <article className="article">
        <div className="prose">
          <p>
            Fielders get no credit yet. Wicket values lean high, because weak sides lose early wickets
            more often. Ratings cannot compare teams that never play each other. Pitch effects are not
            adjusted. Cricket history starts in the early 2000s.
          </p>
        </div>
      </article>
    </>
  );
}

export default async function MethodsPage(props: PageProps) {
  const { sport, q } = await readPage(props);
  const leagues = await leaguesOf(sport);
  const league = q.league || leagues[0].league;
  const model = await api<CricketModel>("models", { sport, league });
  const mens = leagues.map((each) => each.league).filter((name) => !name.endsWith(WOMENS));
  return (
    <>
      <Intro />
      <CricketModelSection model={model} leagues={mens} />
      <DataTable />
      <Limits />
    </>
  );
}
