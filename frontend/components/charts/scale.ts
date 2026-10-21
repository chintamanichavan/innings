// Plain arithmetic for charts. No browser needed, so server-drawn charts can use it too.

export const NARROW = 520; // below this width, labels are shortened

export const clamp = (low: number, value: number, high: number) => Math.max(low, Math.min(high, value));

/** A point as an SVG polyline writes it. */
export const xy = (x: number, y: number) => `${x.toFixed(1)},${y.toFixed(1)}`;
