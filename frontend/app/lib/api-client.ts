const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, path: string) {
    super(`${path} returned ${status}`);
  }
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const timeout = AbortSignal.timeout(15000);
  const res = await fetch(`${API}${path}`, { signal: signal ? AbortSignal.any([signal, timeout]) : timeout });
  if (!res.ok) throw new ApiError(res.status, path);
  return res.json();
}

/** Fetch bounded API pages rather than silently dropping older races or late laps. */
export async function getPages<T>(path: string, pageSize: number, signal?: AbortSignal): Promise<T[]> {
  const result: T[] = [];
  for (let offset = 0; ; offset += pageSize) {
    const page = await getJson<T[]>(`${path}?limit=${pageSize}&offset=${offset}`, signal);
    if (!Array.isArray(page)) throw new Error("Expected a list from the race API");
    result.push(...page);
    if (page.length < pageSize) return result;
  }
}
