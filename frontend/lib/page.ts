// What every page under /[sport] receives, and how it reads it.

import { notFound } from "next/navigation";

import { type Sport, sportOfSlug } from "./sport";

type Params = Record<string, string>;
type Search = Record<string, string | string[] | undefined>;

/** The props Next.js hands a page. Both arrive as promises. */
export interface PageProps<Extra extends Params = Params> {
  params: Promise<{ sport: string } & Extra>;
  searchParams: Promise<Search>;
}

/** The sport, the other address parts (decoded), and the options after the question mark. */
export async function readPage<Extra extends Params = Params>(props: PageProps<Extra>) {
  const { sport: slug, ...rest } = await props.params;
  const sport: Sport | null = sportOfSlug(slug);
  if (!sport) notFound();
  const args = Object.fromEntries(
    Object.entries(rest).map(([key, value]) => [key, decodeURIComponent(String(value))]),
  ) as Extra;
  const q: Record<string, string> = {};
  for (const [key, value] of Object.entries(await props.searchParams)) {
    if (typeof value === "string") q[key] = value;
  }
  return { sport, args, q };
}
