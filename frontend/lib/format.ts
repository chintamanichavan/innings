// Numbers, dates and words, as the reader sees them.

import type { Sport } from "./sport";

/** A sport's own words for roles and ideas. */
export const WORDS: Record<Sport, Record<string, string>> = {
  ck: {
    bat: "Batters",
    bowl: "Bowlers",
    bowler: "Bowler",
    bowling: "Bowling",
    first: "Batting first",
    second: "Chasing",
    chances: "balls",
    faced: "balls bowled",
  },
};

type Maybe = number | null | undefined;
const missing = (value: Maybe): value is null | undefined => value == null || Number.isNaN(value);

export function num(value: Maybe, digits = 0): string {
  if (missing(value)) return "–";
  const places = { minimumFractionDigits: digits, maximumFractionDigits: digits };
  return Number(value).toLocaleString("en-US", places);
}

/** A number with its sign shown, using a true minus. */
export function signed(value: Maybe, digits = 0): string {
  if (missing(value)) return "–";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return sign + num(Math.abs(value), digits);
}

/** A chance as a whole percent. Never says 0% or 100% for something still possible. */
export function pct(chance: Maybe): string {
  if (chance == null) return "–";
  if (chance > 0 && chance < 0.01) return "<1%";
  if (chance < 1 && chance > 0.99) return ">99%";
  return `${Math.round(chance * 100)}%`;
}

/** A stat column, as the server describes it. */
export interface Column {
  key: string;
  label: string;
  digits: number;
}

const SIGNED_COLUMNS = ["rae", "rate", "wpa", "clutch"];

/** One table cell, formatted the way its column expects. */
export function cell(column: Column, value: Maybe): string {
  if (SIGNED_COLUMNS.includes(column.key)) return signed(value, column.digits);
  return num(value, column.digits);
}

function asDate(value: string): Date {
  return new Date(`${String(value).slice(0, 10)}T12:00:00`);
}

export function day(value: string): string {
  return asDate(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function yearOf(value: string): number {
  return asDate(value).getFullYear();
}

export function capital(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// The numbers that carry a sentence, so they can be set in bold.
const KEY_FIGURES = new RegExp(
  [
    String.raw`\b(?:under |over )?\d[\d.,]*%`, // 62%, under 1%
    String.raw`[+−-]\d[\d.,]*(?= (?:runs?|points))`, // +16 points
    String.raw`\b\d[\d,]*–\d[\d,]*\b`, // 6–5
    String.raw`\b\d+ for \d+\b`, // 3 for 21
    String.raw`\b\d+ off \d+ balls\b`, // 143 off 232 balls
    String.raw`\b\d+(?:st|nd|rd|th)\b(?= (?:wildest|of))`, // 2nd of 2,714
    String.raw`\bthe (?:wildest|best)\b(?= of)`,
    String.raw`\b[\d,]+ runs (?:more|fewer)\b`,
    String.raw`\b\d+ wins?, \d+ loss(?:es)?\b`,
    String.raw`\b\d+ of their last 10\b`,
  ].join("|"),
  "g",
);

/** A sentence cut into pieces, each marked as a key figure or not. */
export function keyFigures(sentence: string): { text: string; key: boolean }[] {
  const pieces: { text: string; key: boolean }[] = [];
  let from = 0;
  for (const found of sentence.matchAll(KEY_FIGURES)) {
    if (found.index > from) pieces.push({ text: sentence.slice(from, found.index), key: false });
    pieces.push({ text: found[0], key: true });
    from = found.index + found[0].length;
  }
  if (from < sentence.length) pieces.push({ text: sentence.slice(from), key: false });
  return pieces;
}

/** Cricket writes 14.3 for fourteen overs and three balls. */
export function oversToBalls(text: string): number {
  const overs = parseFloat(text) || 0;
  return Math.floor(overs) * 6 + Math.min(5, Math.round((overs % 1) * 10));
}

export function ballsToOvers(balls: number): string {
  return `${Math.floor(balls / 6)}${balls % 6 ? `.${balls % 6}` : ""}`;
}
