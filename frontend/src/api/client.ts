/** Gọi API của server Python; lỗi HTTP ném Error với thông báo `detail` từ server. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData;
  const res = await fetch(path, {
    ...init,
    headers: init.body && !isForm ? { "Content-Type": "application/json" } : undefined,
  });
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    /* không phải JSON */
  }
  if (!res.ok) {
    const detail = (data as { detail?: string } | null)?.detail;
    throw new Error(detail || res.statusText);
  }
  return data as T;
}

export function send<T>(method: "POST" | "PUT", path: string, body?: unknown): Promise<T> {
  return api<T>(path, { method, body: body instanceof FormData ? body : JSON.stringify(body ?? {}) });
}

/** "live", "bot:<tên>" (journal của từng bot ONE) hoặc run_id của một lần backtest. */
export type Source = string;

export const isLiveSource = (source: Source) => source === "live" || source.startsWith("bot:");

/** mode của API (live | bot:<tên> | backtest) ứng với nguồn. */
export const sourceMode = (source: Source) => (isLiveSource(source) ? source : "backtest");

export function sourceQuery(source: Source): string {
  return isLiveSource(source)
    ? `mode=${encodeURIComponent(source)}`
    : `mode=backtest&run=${encodeURIComponent(source)}`;
}
