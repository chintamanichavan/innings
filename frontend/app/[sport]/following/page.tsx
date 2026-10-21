// The reader's own teams and players. The first-visit sheet that asks for them is in the frame.

import type { Metadata } from "next";

import { EditTeamsButton, PlayerRows, TeamCards } from "./FollowingLists";

export const metadata: Metadata = { title: "Your edition" };

export default function Following() {
  return (
    <>
      <p className="kicker">Following</p>
      <h1 className="page">Your edition</h1>
      <p className="standfirst">Your teams lead the front page. Everything is kept on this device.</p>
      <h2 className="label">Teams</h2>
      <TeamCards />
      <p className="spaced">
        <EditTeamsButton />
      </p>
      <h2 className="label">Players</h2>
      <PlayerRows />
    </>
  );
}
