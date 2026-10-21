// One puzzle game: who, hl or pick.

import type { Metadata } from "next";

import { type PageProps, readPage } from "@/lib/page";

import { PuzzleCorner, gameTitle } from "../PuzzleCorner";

type Props = PageProps<{ game: string }>;

export async function generateMetadata(props: Props): Promise<Metadata> {
  const { args } = await readPage(props);
  return { title: gameTitle(args.game) };
}

export default async function Puzzle(props: Props) {
  const { sport, args } = await readPage(props);
  return <PuzzleCorner sport={sport} arg={args.game} />;
}
