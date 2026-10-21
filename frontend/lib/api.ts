// Talking to the Python server. The same call works in a server component, where it goes
// straight to the server, and in the browser, where it goes through this site's /api.

import { type Query, queryString } from "./sport";

const SERVER_BASE = process.env.API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

/** GET /api/<path> and return the JSON. Throws an ApiError with a readable message. */
export async function api<T>(path: string, params: Query = {}): Promise<T> {
  const base = typeof window === "undefined" ? SERVER_BASE : "";
  const response = await fetch(`${base}/api/${path}${queryString(params)}`, { cache: "no-store" });
  if (response.ok) return response.json() as Promise<T>;
  const problem = (await response.json().catch(() => ({}))) as { detail?: string };
  throw new ApiError(problem.detail ?? "The server did not answer.", response.status);
}
