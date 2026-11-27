// The scorecard in brief, as a match summary shows it: each innings' total, its three best
// batters and its three best bowlers.

import { type InningsCard, type ScorecardData, inningsName, total } from "./types";

const SHOWN = 3;

function Innings({ innings, all }: { innings: InningsCard; all: InningsCard[] }) {
  const batters = [...innings.batting]
    .sort((a, b) => b.runs - a.runs || a.balls - b.balls)
    .slice(0, SHOWN);
  const bowlers = [...innings.bowling]
    .sort((a, b) => b.wickets - a.wickets || a.runs - b.runs)
    .slice(0, SHOWN);
  return (
    <div className="brief">
      <div className="brief-head">
        <b>{inningsName(innings, all)}</b>
        <span>
          {total(innings)} <small>({innings.overs} ov)</small>
        </span>
      </div>
      <div className="brief-cols">
        <div>
          {batters.map((batter) => (
            <p key={batter.player_id}>
              <span>{batter.name}</span>
              <b>
                {batter.runs}
                {batter.out ? "" : "*"}
              </b>
              <small>{batter.balls}</small>
            </p>
          ))}
        </div>
        <div>
          {bowlers.map((bowler) => (
            <p key={bowler.player_id}>
              <span>{bowler.name}</span>
              <b>
                {bowler.wickets}/{bowler.runs}
              </b>
              <small>{bowler.overs}</small>
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ScoreSummary({ data }: { data: ScorecardData }) {
  return (
    <div className="panel briefs">
      {data.innings.map((innings) => (
        <Innings key={innings.number} innings={innings} all={data.innings} />
      ))}
    </div>
  );
}
