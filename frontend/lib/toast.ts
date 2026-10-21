// The two floating messages: the toast and the tooltip. Any code may call these; the
// components in components/Floating.tsx listen and draw them.

export const TOAST_EVENT = "innings:toast";
export const TIP_EVENT = "innings:tip";

export interface Tip {
  title: string;
  text: string;
  x: number;
  y: number;
  fromAttribute?: boolean; // shown by hovering an element, not by a call to showTip
}

export function toast(text: string): void {
  dispatchEvent(new CustomEvent<string>(TOAST_EVENT, { detail: text }));
}

export function showTip(title: string, text: string, x: number, y: number): void {
  dispatchEvent(new CustomEvent<Tip | null>(TIP_EVENT, { detail: { title, text, x, y } }));
}

export function hideTip(): void {
  dispatchEvent(new CustomEvent<Tip | null>(TIP_EVENT, { detail: null }));
}

/** Props that give any element a hover tooltip: <span {...tip("Thrill", "How far...")}>. */
export function tip(title: string, text = ""): { "data-tip-title": string; "data-tip": string } {
  return { "data-tip-title": title, "data-tip": text };
}
