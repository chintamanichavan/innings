// Innings against the betting market: the same Big Bash matches, the same moments, scored by
// one rule. The numbers come shaped from src/innings/web/routes/market.py.

import { Marked } from "@/components/Marked";
import { num, signed } from "@/lib/format";

import { MarketCalibration } from "./MarketCalibration";
import type { MarketPage } from "./types";

const brier = (value: number) => num(value, 3);

export function Market({ market }: { market: MarketPage }) {
  const { matches, calibration_error: error, widest, betting } = market;
  const tied = error.gap_interval[0] < 0 && error.gap_interval[1] > 0;
  const standfirst =
    `Betfair's exchange prices for ${num(matches.scored)} Big Bash matches, 2020/21 to 2025/26, ` +
    `against our chances at the same ten moments of each match. Our models were refitted for this ` +
    `on earlier seasons only, so they never saw these games.`;

  return (
    <section className="spaced">
      <h2 className="label">Against the betting market</h2>
      <p className="prose">
        <Marked text={standfirst} />
      </p>
      <div className="tiles">
        <div className="tile">
          <b>
            {num(error.innings, 3)} / {num(error.market, 3)}
          </b>
          <span>calibration error, ours / the market's. {tied ? "No real difference" : ""}</span>
        </div>
        <div className="tile">
          <b>{signed(widest.gap, 3)}</b>
          <span>our widest accuracy gap, at {widest.label.toLowerCase()}. The market is sharper</span>
        </div>
        <div className="tile">
          <b>{signed(100 * betting.return_per_unit, 1)}%</b>
          <span>
            {`a unit, backing every side we rated ${num(100 * betting.edge)} points above the market ` +
              `(${num(betting.bets)} bets). No edge found`}
          </span>
        </div>
      </div>
      <div className="cols2">
        <section>
          <h3 className="label">Is a 70% chance right 70% of the time?</h3>
          <MarketCalibration bins={market.calibration} />
          <p className="prose small">
            Both are. Every chance is counted from both sides, so it does not matter who is listed
            first.
          </p>
        </section>
        <section>
          <h3 className="label">Closer to what happened, moment by moment</h3>
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th className="l">Moment</th>
                  <th>Matches</th>
                  <th>Ours</th>
                  <th>Market</th>
                  <th>Gap</th>
                </tr>
              </thead>
              <tbody>
                {market.moments.map((moment) => (
                  <tr key={moment.label}>
                    <td className="l">{moment.label}</td>
                    <td>{num(moment.n)}</td>
                    <td>{brier(moment.innings)}</td>
                    <td>{brier(moment.market)}</td>
                    <td title={`95% interval ${signed(moment.low, 3)} to ${signed(moment.high, 3)}`}>
                      {moment.clear ? <b>{signed(moment.gap, 3)}</b> : signed(moment.gap, 3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="prose small">
            Brier score: the average squared miss, lower is better, 0.25 is a coin flip. A gap in bold
            is clearly real; the others could be chance.
          </p>
        </section>
      </div>
      <p className="prose">
        <Marked
          text={
            "So we are as honest about our uncertainty as the market, but it knows more. Our in-play " +
            "model sees only the score; mixing our own team ratings back in closes about a fifth of the " +
            "gap. The rest is what the crowd knows that we do not: the pitch, the weather, who is in form."
          }
        />
      </p>
    </section>
  );
}
