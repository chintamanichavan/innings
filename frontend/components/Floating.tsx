// The toast and the tooltip. One of each lives in the page frame.

"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { TIP_EVENT, TOAST_EVENT, type Tip } from "@/lib/toast";

const TOAST_MS = 2200;

export function Toast() {
  const [text, setText] = useState("");

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const show = (event: Event) => {
      setText((event as CustomEvent<string>).detail);
      clearTimeout(timer);
      timer = setTimeout(() => setText(""), TOAST_MS);
    };
    addEventListener(TOAST_EVENT, show);
    return () => {
      removeEventListener(TOAST_EVENT, show);
      clearTimeout(timer);
    };
  }, []);

  return (
    <div id="toast" role="status" aria-live="polite" hidden={!text}>
      {text}
    </div>
  );
}

/** Shows a tooltip for any element with `data-tip-title`, and for code that calls showTip. */
export function Tips() {
  const [tip, setTip] = useState<Tip | null>(null);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fromCode = (event: Event) => setTip((event as CustomEvent<Tip | null>).detail);
    const fromPointer = (event: MouseEvent) => {
      const owner = (event.target as Element | null)?.closest?.<HTMLElement>("[data-tip-title]");
      if (!owner) {
        setTip((shown) => (shown?.fromAttribute ? null : shown));
        return;
      }
      const { tipTitle = "", tip: text = "" } = owner.dataset;
      setTip({ title: tipTitle, text, x: event.clientX, y: event.clientY, fromAttribute: true });
    };
    addEventListener(TIP_EVENT, fromCode);
    document.addEventListener("mousemove", fromPointer);
    return () => {
      removeEventListener(TIP_EVENT, fromCode);
      document.removeEventListener("mousemove", fromPointer);
    };
  }, []);

  // Keep the tooltip on screen: it is placed after it has been measured.
  useLayoutEffect(() => {
    const element = box.current;
    if (!element || !tip) return;
    const left = Math.min(tip.x + 14, innerWidth - element.offsetWidth - 8);
    element.style.left = `${Math.max(8, left)}px`;
    element.style.top = `${Math.max(8, tip.y - element.offsetHeight - 12)}px`;
  }, [tip]);

  return (
    <div id="tip" ref={box} hidden={!tip}>
      {tip && (
        <>
          <b>{tip.title}</b>
          {tip.text}
        </>
      )}
    </div>
  );
}
