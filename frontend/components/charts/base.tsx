// What every chart shares: fitting its box, and a crosshair that follows the pointer.

"use client";

import { type ReactNode, type RefObject, useLayoutEffect, useRef, useState } from "react";

import { hideTip, showTip } from "@/lib/toast";

export { NARROW, clamp, xy } from "./scale";

/**
 * The real width of a box, kept up to date. A chart draws at this width, so its type is the
 * same size on a phone and on a desk. Zero until the box has been measured.
 */
export function useWidth(): [RefObject<HTMLDivElement | null>, number] {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const element = box.current;
    if (!element) return;
    const measure = () => setWidth(Math.max(300, Math.round(element.clientWidth)));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return [box, width];
}

/** Where the crosshair should sit, and what its tooltip says. */
export interface Mark {
  x: number;
  y: number;
  title: string;
  text: string;
}

interface CrosshairProps {
  width: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
  place: (x: number) => Mark; // the nearest point to a position along the chart
}

/** A dot and a dashed line that follow the pointer, with a tooltip. Goes last inside the svg. */
export function Crosshair({ width, left, right, top, bottom, place }: CrosshairProps) {
  const [mark, setMark] = useState<Mark | null>(null);
  const move = (clientX: number, clientY: number, target: SVGRectElement) => {
    const frame = target.ownerSVGElement!.getBoundingClientRect();
    const at = place(((clientX - frame.left) / frame.width) * width);
    setMark(at);
    showTip(at.title, at.text, clientX, clientY);
  };
  const leave = () => {
    setMark(null);
    hideTip();
  };
  return (
    <>
      {mark && (
        <g className="cross">
          <line className="ref" x1={mark.x} x2={mark.x} y1={top} y2={bottom} />
          <circle
            cx={mark.x}
            cy={mark.y}
            r="5"
            fill="var(--ink)"
            stroke="var(--card)"
            strokeWidth="2"
          />
        </g>
      )}
      <rect
        x={left}
        y={top}
        width={width - left - right}
        height={bottom - top}
        fill="transparent"
        onMouseMove={(event) => move(event.clientX, event.clientY, event.currentTarget)}
        onTouchMove={(event) =>
          move(event.touches[0].clientX, event.touches[0].clientY, event.currentTarget)
        }
        onMouseLeave={leave}
        onTouchEnd={leave}
      />
    </>
  );
}

/** The svg frame of a chart. */
export function Svg({
  width,
  height,
  label,
  children,
}: {
  width: number;
  height: number;
  label: string;
  children: ReactNode;
}) {
  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
      {children}
    </svg>
  );
}
