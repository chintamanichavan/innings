// Tag: the matches a tagger can work on. Not in the menus: it is a tool, not a page to read.

import type { Metadata } from "next";

import { type PageProps, readPage } from "@/lib/page";

import { MatchList } from "./MatchList";

export const metadata: Metadata = { title: "Tag balls" };

export default async function TagPage(props: PageProps) {
  const { sport } = await readPage(props);
  return (
    <>
      <p className="kicker">Ball tagging</p>
      <h1 className="page">Tag balls</h1>
      <p className="standfirst">
        Watch a match you are allowed to watch and record each ball from the keyboard. The pilot is SMAT
        2026 death overs.
      </p>
      <MatchList sport={sport} />
    </>
  );
}
