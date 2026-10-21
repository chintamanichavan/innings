// The sports, and the address of every page.

export type Sport = "ck";

export const SPORTS: Record<Sport, string> = { ck: "Cricket" };

const SLUG: Record<Sport, string> = { ck: "cricket" };
const SPORT_OF: Record<string, Sport> = { cricket: "ck" };

/** The sport a first-time reader lands on. */
export const HOME_SPORT: Sport = "ck";

export function sportOfSlug(slug: string): Sport | null {
  return SPORT_OF[slug] ?? null;
}

export type Query = Record<string, string | number | null | undefined>;

/** A query string from the options that have a value. Starts with "?" unless empty. */
export function queryString(options: Query): string {
  const filled = Object.entries(options).filter(([, value]) => value !== "" && value != null);
  const query = new URLSearchParams(filled.map(([key, value]) => [key, String(value)])).toString();
  return query ? `?${query}` : "";
}

/** The address of a page: /cricket/match/1152848?tab=x. Empty options are left out. */
export function link(sport: Sport, page = "", arg: string | number = "", options: Query = {}): string {
  const parts = [SLUG[sport]];
  if (page && page !== "front") parts.push(page);
  if (arg !== "") parts.push(encodeURIComponent(String(arg)));
  return `/${parts.join("/")}${queryString(options)}`;
}

export function teamHref(sport: Sport, league: string, team: string): string {
  return link(sport, "team", team, { pool: league });
}
