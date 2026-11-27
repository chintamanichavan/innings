// A row of buttons, one per innings, each with its score: "GT 155/8 (20 ov)".

import { type InningsCard, inningsName, total } from "./types";

interface PillsProps {
  all: InningsCard[];
  chosen: number;
  choose: (index: number) => void;
}

export function InningsPills({ all, chosen, choose }: PillsProps) {
  return (
    <div className="pills">
      {all.map((each, index) => (
        <button
          key={each.number}
          className={index === chosen ? "on" : ""}
          onClick={() => choose(index)}
        >
          {inningsName(each, all)} · {total(each)}
          {each.overs && ` (${each.overs} ov)`}
        </button>
      ))}
    </div>
  );
}
