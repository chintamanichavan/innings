// Tag one match, ball by ball, from the keyboard.

import type { Metadata } from "next";

import { type PageProps, readPage } from "@/lib/page";

import { Tagger } from "./Tagger";

export const metadata: Metadata = { title: "Tag balls" };

export default async function TagMatchPage(props: PageProps<{ match: string }>) {
  const { sport, args } = await readPage(props);
  return <Tagger sport={sport} matchId={args.match} />;
}
