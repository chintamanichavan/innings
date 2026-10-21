import type { ReactNode } from "react";

import { type Column, cell } from "@/lib/format";

/** A text column placed before the numbers, such as a player's name. */
export interface Lead<Row> {
  label: string;
  render: (row: Row) => ReactNode;
}

interface StatTableProps<Row> {
  columns: Column[];
  rows: Row[];
  rowKey: (row: Row, index: number) => string | number;
  lead?: Lead<Row>[];
  sort?: string; // the sorted column; makes headers clickable
  ascending?: boolean;
  onSort?: (key: string) => void;
  total?: Row | null; // a bold last row
}

type Numbers = Record<string, number | null | undefined>;

/** A table of stats. `columns` come from the server. */
export function StatTable<Row extends object>(props: StatTableProps<Row>) {
  const {
    columns,
    rows,
    rowKey,
    lead = [],
    sort = "",
    ascending = false,
    onSort,
    total = null,
  } = props;
  const header = (column: Column) => {
    if (!onSort) return <th key={column.key}>{column.label}</th>;
    const sorted = sort === column.key;
    const press = () => onSort(column.key);
    return (
      <th
        key={column.key}
        className={sorted ? "sort sorted" : "sort"}
        tabIndex={0}
        onClick={press}
        onKeyDown={(event) => event.key === "Enter" && press()}
      >
        {column.label}
        {sorted ? (ascending ? " ▲" : " ▼") : ""}
      </th>
    );
  };
  const line = (row: Row, key: string | number, className = "") => (
    <tr key={key} className={className}>
      {lead.map((first) => (
        <td key={first.label} className="l">
          {first.render(row)}
        </td>
      ))}
      {columns.map((column) => (
        <td key={column.key}>{cell(column, (row as Numbers)[column.key])}</td>
      ))}
    </tr>
  );
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            {lead.map((first) => (
              <th key={first.label} className="l">
                {first.label}
              </th>
            ))}
            {columns.map(header)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => line(row, rowKey(row, index)))}
          {total && line(total, "total", "total")}
        </tbody>
      </table>
    </div>
  );
}
