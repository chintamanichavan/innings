// Animation helpers. Every one of them respects the reader's "reduce motion" setting:
// with it on, things appear in their final state at once.

export function reducedMotion(): boolean {
  return matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Slow at both ends, quick in the middle. `t` runs from 0 to 1. */
export function ease(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
}

/**
 * Call `frame(progress)` on every animation frame, with progress running from 0 to 1 over
 * `milliseconds`. Returns a function that stops it. Stops by itself if `alive()` turns false,
 * which is how an animation ends when the reader leaves the page.
 */
export function animate(
  milliseconds: number,
  frame: (progress: number) => void,
  { alive = () => true, done = () => {} }: { alive?: () => boolean; done?: () => void } = {},
): () => void {
  if (reducedMotion()) {
    frame(1);
    done();
    return () => {};
  }
  let stopped = false;
  const started = performance.now();
  const step = (now: number) => {
    if (stopped || !alive()) return;
    // A frame's clock can read slightly earlier than `started`, so hold progress at zero or above.
    const progress = Math.min(1, Math.max(0, (now - started) / milliseconds));
    frame(progress);
    if (progress < 1) requestAnimationFrame(step);
    else done();
  };
  requestAnimationFrame(step);
  return () => {
    stopped = true;
  };
}

/** Run `start` once, the first time the element scrolls into view. */
export function whenVisible(element: Element, start: () => void): () => void {
  const observer = new IntersectionObserver(
    (entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      start();
    },
    { threshold: 0.35 },
  );
  observer.observe(element);
  return () => observer.disconnect();
}

/**
 * Count every element with a `data-count` attribute up from zero to its number, when it
 * scrolls into view. `data-digits` sets decimal places; `data-suffix` is added after.
 */
export function countUp(root: ParentNode): void {
  for (const element of root.querySelectorAll<HTMLElement>("[data-count]")) {
    const target = Number(element.dataset.count);
    const digits = Number(element.dataset.digits || 0);
    const suffix = element.dataset.suffix || "";
    const show = (value: number) => {
      const places = { minimumFractionDigits: digits, maximumFractionDigits: digits };
      element.textContent = value.toLocaleString("en-US", places) + suffix;
    };
    show(reducedMotion() ? target : 0);
    whenVisible(element, () =>
      animate(900, (progress) => show(target * ease(progress)), {
        alive: () => element.isConnected,
      }),
    );
  }
}

/** The colour a CSS variable currently has, as [red, green, blue]. Canvas cannot read variables. */
export type Rgb = [red: number, green: number, blue: number];

export function themeColor(name: string): Rgb {
  const probe = document.createElement("span");
  probe.style.color = `var(${name})`;
  document.body.appendChild(probe);
  const [red = 0, green = 0, blue = 0] = (getComputedStyle(probe).color.match(/[\d.]+/g) ?? []).map(
    Number,
  );
  probe.remove();
  return [red, green, blue];
}

/** One colour, as a CSS string. */
export function solid(color: Rgb, alpha = 1): string {
  return blend(color, color, 0, alpha);
}

/** A colour part-way from one [r, g, b] to another, as a CSS string. `alpha` is optional. */
export function blend(from: Rgb, to: Rgb, amount: number, alpha = 1): string {
  const channel = (index: number) => Math.round(from[index] + (to[index] - from[index]) * amount);
  return `rgb(${channel(0)} ${channel(1)} ${channel(2)} / ${alpha})`;
}

/** Size a canvas to its box, sharp on high-density screens. Returns { context, width, height }. */
export function prepareCanvas(canvas: HTMLCanvasElement, height: number) {
  const width = canvas.clientWidth;
  const density = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * density);
  canvas.height = Math.round(height * density);
  canvas.style.height = `${height}px`;
  const context = canvas.getContext("2d")!;
  context.setTransform(density, 0, 0, density, 0, 0);
  return { context, width, height };
}
