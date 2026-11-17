export type FieldMeasure = {
  strict13m?: boolean; dbhCm: string; note: string; heightM: string; coeff: string; measuredAt: string;
};
type Measures = Record<string, FieldMeasure>;
type Pending = Record<string, Partial<FieldMeasure>>;
export type SyncSnapshot = {
  measures: Measures;
  storage: "cosmos" | "file" | "unknown";
  syncState: "loading" | "saved" | "pending" | "saving" | "error";
  error: string;
};

function merge(measures: Measures, pending: Pending): Measures {
  const result = { ...measures };
  for (const [id, patch] of Object.entries(pending)) result[id] = {
    ...(result[id] ?? { dbhCm: "", note: "", heightM: "", coeff: "", measuredAt: "", strict13m: false }), ...patch,
  };
  return result;
}

/** Only explicit edits are queued; viewing a scan never uploads cached records. */
export class FieldMeasureSync {
  snapshot: SyncSnapshot;
  private pending: Pending;
  private ready = false;
  private running: Promise<void> | null = null;
  private loading: Promise<void> | null = null;
  private listeners = new Set<() => void>();
  private readonly cacheKey: string;
  private readonly pendingKey: string;
  private readonly scanId: string;
  private readonly cache: Pick<Storage, "getItem" | "setItem">;
  private readonly request: typeof fetch;
  constructor(scanId: string, cache: Pick<Storage, "getItem" | "setItem">, request: typeof fetch = fetch) {
    this.scanId = scanId; this.cache = cache;
    // Browser fetch rejects a controller instance as its receiver.
    this.request = (input, init) => request(input, init);
    this.cacheKey = `arbor3d.fieldMeasures.${scanId}`;
    this.pendingKey = `${this.cacheKey}.pending.v1`;
    this.pending = this.read<Pending>(this.pendingKey);
    this.snapshot = { measures: merge(this.read<Measures>(this.cacheKey), this.pending),
      storage: "unknown", syncState: "loading", error: "" };
  }
  private read<T extends object>(key: string): T {
    try {
      const value = JSON.parse(this.cache.getItem(key) || "{}");
      return value && typeof value === "object" && !Array.isArray(value) ? value as T : {} as T;
    } catch { return {} as T; }
  }
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  getSnapshot = () => this.snapshot;
  private set(patch: Partial<SyncSnapshot>) {
    this.snapshot = { ...this.snapshot, ...patch };
    for (const listener of this.listeners) listener();
  }
  private persist() {
    try {
      this.cache.setItem(this.pendingKey, JSON.stringify(this.pending));
      this.cache.setItem(this.cacheKey, JSON.stringify(this.snapshot.measures));
    } catch { this.set({ error: "瀏覽器暫存空間不足，請保持此頁開啟並完成同步。" }); }
  }
  update = (treeId: string, changes: Partial<FieldMeasure>) => {
    this.pending = { ...this.pending, [treeId]: { ...this.pending[treeId], ...changes } };
    this.set({ measures: merge(this.snapshot.measures, { [treeId]: changes }), syncState: "pending", error: "" });
    this.persist();
  };
  load = (): Promise<void> => {
    if (this.loading) return this.loading;
    this.loading = (async () => {
      try {
        const response = await this.request(`/api/field-measures?scanId=${encodeURIComponent(this.scanId)}`, {
          credentials: "same-origin", signal: AbortSignal.timeout(15000),
        });
        if (!response.ok) throw new Error(response.status === 401 ? "請重新登入後再同步。" : "無法讀取資料庫，修改已保留在此瀏覽器。");
        const body = await response.json() as { measures: Measures; storage: "cosmos" | "file" };
        this.ready = true;
        this.set({ measures: merge(body.measures, this.pending), storage: body.storage,
          syncState: Object.keys(this.pending).length ? "pending" : "saved", error: "" });
        this.persist();
      } catch (error) {
        this.ready = false;
        this.set({ syncState: "error", error: error instanceof Error ? error.message : "連線失敗，修改尚未同步。" });
      } finally { this.loading = null; }
    })();
    return this.loading;
  };
  flush = (): Promise<void> => {
    if (this.running) return this.running;
    this.running = (async () => {
      try {
        if (this.loading) await this.loading;
        if (!this.ready) await this.load();
        if (!this.ready) return;
        while (Object.keys(this.pending).length) {
          const treeId = Object.keys(this.pending)[0];
          const changes = { ...this.pending[treeId] };
          this.set({ syncState: "saving", error: "" });
          const response = await this.request(`/api/field-measures?scanId=${encodeURIComponent(this.scanId)}`, {
            method: "PATCH", credentials: "same-origin", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ treeId, changes }), signal: AbortSignal.timeout(15000),
          });
          if (!response.ok) throw new Error(response.status === 401 ? "請重新登入後再同步。" : "儲存失敗，修改已保留，請重試。");
          const body = await response.json() as { measures: Measures; storage: "cosmos" | "file" };
          const remaining = { ...this.pending[treeId] };
          for (const key of Object.keys(changes) as Array<keyof FieldMeasure>) {
            if (remaining[key] === changes[key]) delete remaining[key];
          }
          if (Object.keys(remaining).length) this.pending[treeId] = remaining;
          else delete this.pending[treeId];
          this.set({ measures: merge(body.measures, this.pending), storage: body.storage,
            syncState: Object.keys(this.pending).length ? "pending" : "saved" });
          this.persist();
        }
      } catch (error) {
        this.set({ syncState: "error", error: error instanceof Error ? error.message : "修改尚未同步，請重試。" });
      }
    })().finally(() => { this.running = null; });
    return this.running;
  };
}

const controllers = new WeakMap<object, Map<string, FieldMeasureSync>>();
export function fieldMeasureSync(scanId: string, cache: Pick<Storage, "getItem" | "setItem">) {
  let scans = controllers.get(cache);
  if (!scans) { scans = new Map(); controllers.set(cache, scans); }
  let sync = scans.get(scanId);
  if (!sync) { sync = new FieldMeasureSync(scanId, cache); scans.set(scanId, sync); }
  return sync;
}
