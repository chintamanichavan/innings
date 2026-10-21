import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { Intro } from "@/components/frame/Intro";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Innings", template: "%s · Innings" },
  description: "Cricket, told through win chance. Stories, forecasts, records and daily puzzles.",
  openGraph: { siteName: "Innings", type: "article" },
  icons: { icon: "/icon.svg", apple: "/icon-180.png" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8f7f6" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
};

// Runs before the page paints, so a reader who chose dark never sees a flash of light.
const APPLY_THEME = `try { const t = localStorage.getItem("innings.theme");
  if (t) document.documentElement.dataset.theme = JSON.parse(t); } catch {}`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {["ball", "bat", "helmet"].map((part) => (
          <link key={part} rel="preload" href={`/intro/${part}.webp`} as="image" type="image/webp" />
        ))}
        <link rel="preload" href="/fonts/geist.woff" as="font" type="font/woff" crossOrigin="" />
        <script dangerouslySetInnerHTML={{ __html: APPLY_THEME }} />
      </head>
      <body>
        <Intro />
        {children}
      </body>
    </html>
  );
}
