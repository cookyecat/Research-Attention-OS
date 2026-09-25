export const API = process.env.NEXT_PUBLIC_API_BASE || "/api";

type ApiCacheEntry = {
  expiresAt: number;
  value?: unknown;
  promise?: Promise<unknown>;
};

const apiCache = new Map<string, ApiCacheEntry>();

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function cachedApi<T>(
  path: string,
  ttlMs = 10_000,
): Promise<T> {
  const now = Date.now();
  const cached = apiCache.get(path);
  if (cached?.value !== undefined && cached.expiresAt > now) {
    return cached.value as T;
  }
  if (cached?.promise) return cached.promise as Promise<T>;

  const promise = api<T>(path)
    .then((value) => {
      apiCache.set(path, {
        value,
        expiresAt: Date.now() + Math.max(0, ttlMs),
      });
      return value;
    })
    .catch((error) => {
      apiCache.delete(path);
      throw error;
    });

  apiCache.set(path, {
    promise,
    expiresAt: now + Math.max(0, ttlMs),
  });
  return promise;
}

export function invalidateApiCache(prefix?: string): void {
  if (!prefix) {
    apiCache.clear();
    return;
  }
  for (const key of apiCache.keys()) {
    if (key.startsWith(prefix)) apiCache.delete(key);
  }
}

export async function apiOrNull<T>(path: string, init?: RequestInit): Promise<T | null> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}
