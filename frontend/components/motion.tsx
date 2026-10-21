// Small moving parts that any page can use. Each respects the reader's reduce-motion setting.

"use client";

import { useEffect, useRef, useState } from "react";

import { num } from "@/lib/format";
import { animate, ease, whenVisible } from "@/lib/motion";

const COUNT_MS = 900;

/** A number that counts up from zero when it scrolls into view. */
export function CountUp({ value, digits = 0 }: { value: number; digits?: number }) {
  const element = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(value); // the server draws the final number
  useEffect(() => {
    let stop = () => {};
    const unwatch = whenVisible(element.current!, () => {
      stop = animate(COUNT_MS, (progress) => setShown(value * ease(progress)));
    });
    return () => {
      unwatch();
      stop();
    };
  }, [value]);
  return <b ref={element}>{num(shown, digits)}</b>;
}

/** A bar that grows to `percent` of its track when it scrolls into view. */
export function GrowBar({ percent }: { percent: number }) {
  const element = useRef<HTMLElement>(null);
  const [grown, setGrown] = useState(false);
  useEffect(() => whenVisible(element.current!, () => setGrown(true)), []);
  return <i ref={element} style={{ width: grown ? `${percent}%` : 0 }} />;
}
