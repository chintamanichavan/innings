import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { Tips, Toast } from "@/components/Floating";
import { Mast } from "@/components/frame/Mast";
import { ServiceWorker } from "@/components/frame/ServiceWorker";
import { TabBar } from "@/components/frame/TabBar";
import { TeamSheet } from "@/components/frame/TeamSheet";
import { link, sportOfSlug } from "@/lib/sport";

interface FrameProps {
  children: ReactNode;
  params: Promise<{ sport: string }>;
}

/** The frame around every page of one sport. */
export default async function Frame({ children, params }: FrameProps) {
  const sport = sportOfSlug((await params).sport);
  if (!sport) notFound();
  return (
    <>
      <a className="skip" href="#view">
        Skip to content
      </a>
      <Mast sport={sport} />
      <main id="view" tabIndex={-1}>
        {children}
      </main>
      <footer className="colophon">
        <p>
          <b>Innings</b> tells cricket through win chance.{" "}
          <Link href={link("ck", "methods")}>How it works</Link>
        </p>
        <p>
          Cricket: ball-by-ball data from <a href="https://cricsheet.org">Cricsheet</a>, under the ODC
          Attribution License.
        </p>
      </footer>
      <TabBar sport={sport} />
      <TeamSheet />
      <Toast />
      <Tips />
      <ServiceWorker />
    </>
  );
}
