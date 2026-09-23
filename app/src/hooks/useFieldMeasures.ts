import { useCallback, useEffect, useState } from "react";

export type FieldMeasure = {
  strict13m?: boolean;
  dbhCm: string;
  note: string;
  heightM: string;
  coeff: string;
  measuredAt: string;
};

type Store = Record<string, FieldMeasure>;

function keyFor(scanId: string) {
  return `arbor3d.fieldMeasures.${scanId}`;
}

function readStore(scanId: string): Store {
  try {
    const raw = localStorage.getItem(keyFor(scanId));
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Store;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeStore(scanId: string, store: Store) {
  localStorage.setItem(keyFor(scanId), JSON.stringify(store));
}

export function useFieldMeasures(scanId: string) {
  const [measures, setMeasures] = useState<Store>(() => readStore(scanId));
  const [serverReady, setServerReady] = useState(false);
  const [storage, setStorage] = useState<"cosmos" | "file" | "unknown">("unknown");

  useEffect(() => {
    let active = true;
    const local = readStore(scanId);
    setMeasures(local);
    setServerReady(false);
    setStorage("unknown");
    void fetch(`/api/field-measures?scanId=${encodeURIComponent(scanId)}`, {
      credentials: "same-origin",
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("無法讀取伺服器量測");
        return response.json() as Promise<{
          measures?: Store;
          storage?: "cosmos" | "file";
        }>;
      })
      .then((body) => {
        if (!active) return;
        const merged = { ...(body.measures ?? {}), ...local };
        writeStore(scanId, merged);
        setMeasures(merged);
        if (body.storage === "cosmos" || body.storage === "file") {
          setStorage(body.storage);
        }
      })
      .catch(() => {
        if (active) setStorage("file");
      })
      .finally(() => {
        if (active) setServerReady(true);
      });
    return () => {
      active = false;
    };
  }, [scanId]);

  useEffect(() => {
    if (!serverReady) return;
    const sync = () => {
      void fetch(`/api/field-measures?scanId=${encodeURIComponent(scanId)}`, {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ measures }),
      })
        .then(async (response) => {
          if (!response.ok) return;
          const body = (await response.json()) as { storage?: "cosmos" | "file" };
          if (body.storage === "cosmos" || body.storage === "file") {
            setStorage(body.storage);
          }
        })
        .catch(() => undefined);
    };
    const timer = window.setTimeout(sync, 600);
    window.addEventListener("online", sync);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("online", sync);
    };
  }, [measures, scanId, serverReady]);

  const update = useCallback(
    (treeId: string, patch: Partial<FieldMeasure>) => {
      setMeasures((prev) => {
        const next = {
          ...prev,
          [treeId]: {
            strict13m: prev[treeId]?.strict13m ?? false,
            dbhCm: prev[treeId]?.dbhCm ?? "",
            note: prev[treeId]?.note ?? "",
            heightM: prev[treeId]?.heightM ?? "",
            coeff: prev[treeId]?.coeff ?? "",
            measuredAt: prev[treeId]?.measuredAt ?? "",
            ...patch,
          },
        };
        writeStore(scanId, next);
        return next;
      });
    },
    [scanId],
  );

  return { measures, update, storage };
}
