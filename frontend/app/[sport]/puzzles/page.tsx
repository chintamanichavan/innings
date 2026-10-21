// The puzzle corner with no game chosen: the first game, Who am I?

import type { Metadata } from "next";

import { type PageProps, readPage } from "@/lib/page";

import { PuzzleCorner, gameTitle } from "./PuzzleCorner";

export const metadata: Metadata = { title: gameTitle("who") };

export default async function Puzzles(props: PageProps) {
  const { sport } = await readPage(props);
  return <PuzzleCorner sport={sport} arg="who" />;
}
