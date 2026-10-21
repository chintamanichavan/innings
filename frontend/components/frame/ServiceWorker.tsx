"use client";

import { useEffect } from "react";

/** Keeps fonts and icons on the device, so a repeat visit paints at once. */
export function ServiceWorker() {
  useEffect(() => {
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  }, []);
  return null;
}
