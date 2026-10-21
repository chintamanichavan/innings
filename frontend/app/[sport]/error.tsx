"use client";

import Link from "next/link";

export default function PageError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <>
      <p className="kicker">Something went wrong</p>
      <h1 className="page">We could not load this page</h1>
      <p className="standfirst">{error.message}</p>
      <p className="row spaced">
        <button className="btn" onClick={reset}>
          Try again
        </button>
        <Link className="btn alt" href="/">
          Front page
        </Link>
      </p>
    </>
  );
}
