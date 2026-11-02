import { callable } from "@decky/api";
const request = callable<[operation: string, payload: Record<string, unknown>], {ok: boolean; data?: unknown; error?: string}>("request");
export async function rpc<T>(operation: string, payload: Record<string, unknown> = {}): Promise<T> {
  const r = await request(operation, payload);
  if (!r.ok) throw new Error(r.error || "Backend error");
  return r.data as T;
}
