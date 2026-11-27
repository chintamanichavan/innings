// A slice's table: one line per part, then the whole slice in bold. A click on a column
// header ranks by it.

"use client";

import Link from "next/link";

import { useSetQuery } from "@/components/controls";
import { StatTable, type Lead } from "@/components/StatTable";
import { PlayerLink } from "@/components/teams";
import { type SliceAnswer, type SliceRow, needsStyles } from "@/lib/slices";
import { type Sport, link } from "@/lib/sport";

const PLAYER_SPLITS = ["batter", "bowler", "player"];

function RowName({ sport, by, row }: { sport: Sport; by: string; row: SliceRow }) {
  if (PLAYER_SPLITS.includes(by)) return <PlayerLink sport={sport} id={row.key} name={row.label} />;
  if (by === "innings") {
    const [player, match] = row.key.split("|");
    const [name, game] = row.label.split(" · ");
    return (
      <>
        <PlayerLink sport={sport} id={player} name={name} />{" "}
        <Link className="dim" href={link(sport, "match", match)}>
          {game}
        </Link>
      </>
    );
  }
  return <>{row.label}</>;
}

interface SliceTableProps {
  sport: Sport;
  answer: SliceAnswer;
  sort: string;
  sortable?: boolean;
  withTotal?: boolean; // the bold line for the whole slice
  only?: string[]; // show just these columns
}

export function SliceTable(props: SliceTableProps) {
  const { sport, answer, sort, sortable = true, withTotal = true, only } = props;
  const setQuery = useSetQuery();
  const by = answer.slice.by ?? "";
  const total = { ...answer.total, key: "total", label: "All" } as SliceRow;
  if (!answer.total.balls) return <p className="empty">No balls match. Widen the filters.</p>;
  const lead: Lead<SliceRow>[] = [
    { label: "", render: (row) => <RowName sport={sport} by={by} row={row} /> },
  ];
  const styles = needsStyles(answer.slice);
  const known = styles.type ? answer.coverage.type : styles.hand ? answer.coverage.hand : null;
  return (
    <>
      <StatTable
        columns={only ? answer.columns.filter((column) => only.includes(column.key)) : answer.columns}
        rows={answer.rows}
        rowKey={(row) => row.key}
        lead={lead}
        total={withTotal ? total : null}
        sort={sortable ? sort : ""}
        onSort={sortable && by ? (key) => setQuery({ sort: key === sort ? "" : key }) : undefined}
      />
      {answer.min > 0 && by && (
        <p className="note">Rows with fewer than {answer.min} balls are left out.</p>
      )}
      {known != null && <StylesNote answer={answer} everywhere={known} type={styles.type} />}
    </>
  );
}

/**
 * How much of the data a styles split or filter can see. A split names its own share: the
 * balls in its rows out of the whole slice. A filter can only quote the share across all balls.
 */
function StylesNote(props: { answer: SliceAnswer; everywhere: number; type: boolean }) {
  const { answer, everywhere, type } = props;
  const what = type ? "the bowler's type" : "the batter's hand";
  const split = ["type", "family", "hand"].includes(answer.slice.by ?? "");
  const placed = answer.rows.reduce((sum, row) => sum + (row.balls ?? 0), 0);
  const share = (part: number) => `${Math.round(part * 100)}%`;
  return (
    <p className="note">
      {split
        ? `We know ${what} for ${share(placed / (answer.total.balls ?? 1))} of these balls. ` +
          "The rest count in the total but in no row."
        : `Only balls where we know ${what} are counted: ${share(everywhere)} of all balls.`}
    </p>
  );
}
