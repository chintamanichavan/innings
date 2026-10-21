// Small controls shared by many pages.

"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useCallback, useState } from "react";

import { type Query, queryString } from "@/lib/sport";
import { useOnDevice } from "@/lib/store";
import { toast } from "@/lib/toast";

/** Links styled as a row of pills, the current one filled in. */
export function Pills({
  items,
  current,
}: {
  items: [key: string, label: ReactNode, href: string][];
  current: string;
}) {
  return (
    <div className="pills">
      {items.map(([key, label, href]) => (
        <Link key={key} className={key === current ? "on" : ""} href={href} scroll={false}>
          {label}
        </Link>
      ))}
    </div>
  );
}

/** An <option> list. An item is a value, or a [value, label] pair. */
export function Options({ items }: { items: (string | number | [string | number, string])[] }) {
  return (
    <>
      {items.map((item) => {
        const [value, label] = Array.isArray(item) ? item : [item, String(item)];
        return (
          <option key={value} value={value}>
            {label}
          </option>
        );
      })}
    </>
  );
}

/**
 * Change some options on the current page, such as a filter. The address changes in place,
 * so the page keeps its scroll position and Back does not step through every filter.
 */
export function useSetQuery(): (changes: Query) => void {
  const router = useRouter();
  const pathname = usePathname();
  const current = useSearchParams();
  return useCallback(
    (changes: Query) => {
      const merged = { ...Object.fromEntries(current), ...changes };
      router.replace(pathname + queryString(merged), { scroll: false });
    },
    [router, pathname, current],
  );
}

/** Share the current page: the device's share sheet if it has one, else copy the link. */
export function ShareButton({ title }: { title: string }) {
  const share = async () => {
    try {
      if (navigator.share) await navigator.share({ title, url: location.href });
      else {
        await navigator.clipboard.writeText(location.href);
        toast("Link copied");
      }
    } catch {
      // The reader closed the share sheet. Nothing to do.
    }
  };
  return (
    <button className="btn alt sm" onClick={share}>
      <svg viewBox="0 0 20 20" width="15" height="15" aria-hidden="true">
        <path
          d="M10 13V3m0 0L6.5 6.5M10 3l3.5 3.5M4 11v5h12v-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      Share
    </button>
  );
}

/**
 * A Follow button. `isFollowing` reads the device; `toggle` flips it and returns the new
 * state. Before the page has loaded on the device it shows "Follow".
 */
export function FollowButton({
  isFollowing,
  toggle,
}: {
  isFollowing: () => boolean;
  toggle: () => boolean;
}) {
  const onDevice = useOnDevice();
  const [, redraw] = useState(0);
  const following = onDevice && isFollowing();
  const press = () => {
    toggle();
    redraw((count) => count + 1);
  };
  return (
    <button className={`btn sm follow ${following ? "on" : "alt"}`} onClick={press}>
      {following ? "Following" : "Follow"}
    </button>
  );
}
