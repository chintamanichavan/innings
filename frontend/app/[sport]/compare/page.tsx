// Two players side by side: the same five skills, ranked within each player's format.

import type { Metadata } from "next";
import { Fragment, cache } from "react";

import { SkillBars } from "@/components/charts/small";
import { StatTable } from "@/components/StatTable";
import { api } from "@/lib/api";
import { type PageProps, readPage } from "@/lib/page";
import type { Sport } from "@/lib/sport";

import type { Basics, Extra, Profile, Role, RoleTable } from "../player/[id]/types";
import { Pickers } from "./Pickers";

interface Side {
  id: string;
  name: string;
  roles: Basics["roles"];
  profile: Extra["profile"];
}

const ROLES: Role[] = ["bat", "bowl"];

/** Older links wrote the player as "ck:<id>". */
const idOf = (text: string) => text.replace(/^ck:/, "");

const loadSide = cache(async (sport: Sport, text: string | undefined): Promise<Side | null> => {
  if (!text) return null;
  const id = idOf(text);
  const path = `${sport}/${encodeURIComponent(id)}`;
  const [basics, extra] = await Promise.all([
    api<Basics>(`player/${path}`),
    api<Extra>(`player-extra/${path}`),
  ]);
  return { id, name: basics.name, roles: basics.roles, profile: extra.profile };
});

const titleOf = (first: Side | null, second: Side | null) =>
  first && second ? `${first.name} and ${second.name}` : "Any two players";

export async function generateMetadata(props: PageProps): Promise<Metadata> {
  const { sport, q } = await readPage(props);
  const [first, second] = await Promise.all([loadSide(sport, q.a), loadSide(sport, q.b)]);
  return { title: titleOf(first, second) };
}

const formatOf = (player: Side, role: Role) => `${player.profile[role]?.fmt} cricket`;

function CareerLine({ player, role }: { player: Side; role: Role }) {
  const table: RoleTable | undefined = player.roles[role];
  if (!table) return null;
  return (
    <>
      <h2 className="label">{player.name}, career</h2>
      <StatTable columns={table.columns} rows={[table.total]} rowKey={() => "career"} />
    </>
  );
}

function RoleComparison({ first, second, role }: { first: Side; second: Side; role: Role }) {
  const title = role === "bat" ? "Batting" : "Bowling";
  const dims = (player: Side) => (player.profile[role] as Profile).dims;
  return (
    <>
      <h2 className="label">{title} profile</h2>
      <div className="legend">
        <span>
          <i style={{ background: "var(--series-1)" }} />
          {first.name} · {formatOf(first, role)}
        </span>
        <span>
          <i style={{ background: "var(--series-2)" }} />
          {second.name} · {formatOf(second, role)}
        </span>
      </div>
      <div className="panel narrow">
        <SkillBars skills={dims(first)} other={dims(second)} />
      </div>
      <p className="note">Each rank is against players in that player&apos;s own format.</p>
      <CareerLine player={first} role={role} />
      <CareerLine player={second} role={role} />
    </>
  );
}

function Comparison({ first, second }: { first: Side | null; second: Side | null }) {
  if (!first || !second) return <p className="empty">Pick two players to compare.</p>;
  const shared = ROLES.filter((role) => first.profile[role] && second.profile[role]);
  if (!shared.length) {
    return <p className="empty">These two do not share a role with enough games to compare.</p>;
  }
  return (
    <>
      {shared.map((role) => (
        <Fragment key={role}>
          <RoleComparison first={first} second={second} role={role} />
        </Fragment>
      ))}
    </>
  );
}

export default async function Compare(props: PageProps) {
  const { sport, q } = await readPage(props);
  const [first, second] = await Promise.all([loadSide(sport, q.a), loadSide(sport, q.b)]);
  return (
    <>
      <p className="kicker">Compare</p>
      <h1 className="page">{titleOf(first, second)}</h1>
      <p className="standfirst">The profile ranks the same five skills for both.</p>
      <Pickers first={first?.name} second={second?.name} />
      <Comparison first={first} second={second} />
    </>
  );
}
