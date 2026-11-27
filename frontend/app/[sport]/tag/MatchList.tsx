// The tagger's name, kept on this device, and the season's matches with their progress.

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { type Sport, link } from "@/lib/sport";
import { store, useStored } from "@/lib/store";
import type { TagMatchSummary } from "@/lib/tagging";

export function MatchList({ sport }: { sport: Sport }) {
  const tagger = useStored("tagger", "");
  const [matches, setMatches] = useState<TagMatchSummary[] | null>(null);
  const [problem, setProblem] = useState("");
  useEffect(() => {
    api<TagMatchSummary[]>("tag/matches", { tagger })
      .then(setMatches)
      .catch((error: Error) => setProblem(error.message));
  }, [tagger]);
  return (
    <>
      <div className="filters">
        <label>
          Your tagger name{" "}
          <input
            value={tagger}
            placeholder="e.g. kc"
            maxLength={32}
            onChange={(event) =>
              store.set("tagger", event.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))
            }
          />
        </label>
      </div>
      {problem && <p className="note">{problem}</p>}
      {!tagger && (
        <p className="note">Pick a short name first. Each tagger sees only their own tags.</p>
      )}
      {tagger && matches && (
        <div className="scroll">
          <table className="card-table">
            <thead>
              <tr>
                <th className="l">Match</th>
                <th className="l">Date</th>
                <th>Death balls</th>
                <th>Tagged</th>
              </tr>
            </thead>
            <tbody>
              {matches.map((match) => (
                <tr key={match.match_id}>
                  <td className="l">
                    <Link className="strong" href={link(sport, "tag", match.match_id)}>
                      {match.team1} v {match.team2}
                    </Link>
                    <small>{match.venue}</small>
                  </td>
                  <td className="l">{match.date}</td>
                  <td>{match.death}</td>
                  <td>{match.tagged || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
