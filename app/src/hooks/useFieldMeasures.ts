import { useEffect, useMemo, useSyncExternalStore } from "react";
import { fieldMeasureSync } from "../lib/fieldMeasureSync";
export type { FieldMeasure } from "../lib/fieldMeasureSync";

export function useFieldMeasures(scanId: string) {
  const sync = useMemo(() => fieldMeasureSync(scanId, localStorage), [scanId]);
  const snapshot = useSyncExternalStore(sync.subscribe, sync.getSnapshot);
  useEffect(() => {
    void sync.load();
    const online = () => { void sync.flush(); };
    window.addEventListener("online", online);
    return () => { window.removeEventListener("online", online); };
  }, [sync]);
  useEffect(() => {
    if (snapshot.syncState !== "pending") return;
    const timer = window.setTimeout(() => { void sync.flush(); }, 600);
    return () => window.clearTimeout(timer);
  }, [sync, snapshot]);
  return { ...snapshot, update: sync.update, retrySync: sync.flush };
}
