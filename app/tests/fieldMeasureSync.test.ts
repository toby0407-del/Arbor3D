import assert from "node:assert/strict";
import test from "node:test";
import { FieldMeasureSync, type FieldMeasure } from "../src/lib/fieldMeasureSync.ts";

const row = (dbhCm: string): FieldMeasure => ({ dbhCm, note: "", heightM: "8", measuredAt: "2026-10-27", coeff: "", strict13m: true });
function cache() {
  const items = new Map<string, string>();
  return { getItem: (key: string) => items.get(key) ?? null, setItem: (key: string, value: string) => { items.set(key, value); } };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(r=>{resolve=r;});
  return { promise, resolve };
}

test("the request function is invoked without the sync controller as its receiver", async () => {
  const sync = new FieldMeasureSync("scan", cache(), async function(this: unknown) {
    assert.equal(this, undefined);
    return Response.json({ measures: {}, storage: "cosmos" });
  });
  await sync.load();
  assert.equal(sync.snapshot.syncState, "saved");
});

test("opening a scan reads the cloud without uploading stale cached measurements", async () => {
  const local = cache();
  local.setItem("arbor3d.fieldMeasures.scan", JSON.stringify({ Tree_001: row("12") }));
  const methods: string[] = [];
  const sync = new FieldMeasureSync("scan", local, async(_url, init)=>{
    methods.push(init?.method || "GET");
    return Response.json({ measures: { Tree_001: row("24") }, storage: "cosmos" });
  });
  await sync.load(); await sync.flush();
  assert.equal(sync.snapshot.measures.Tree_001.dbhCm, "24");
  assert.equal(sync.snapshot.syncState, "saved");
  assert.deepEqual(methods, ["GET"]);
});

test("typing while the cloud read is pending preserves edits and unrelated cloud fields", async () => {
  const read = deferred<Response>();
  const sync = new FieldMeasureSync("scan", cache(), async()=>read.promise);
  const loading = sync.load();
  sync.update("Tree_001", { dbhCm: "26" });
  read.resolve(Response.json({ measures: { Tree_001: { ...row("24"), note: "other user" } }, storage: "cosmos" }));
  await loading;
  assert.equal(sync.snapshot.measures.Tree_001.dbhCm, "26");
  assert.equal(sync.snapshot.measures.Tree_001.note, "other user");
  assert.equal(sync.snapshot.syncState, "pending");
});

test("an idle connectivity retry cannot block the next actual edit", async () => {
  let writes = 0;
  const sync = new FieldMeasureSync("scan", cache(), async(_url, init)=>{
    if (init?.method === "PATCH") writes += 1;
    return Response.json({ measures: { Tree_001: row(writes ? "28" : "24") }, storage: "cosmos" });
  });
  await sync.load(); await sync.flush();
  sync.update("Tree_001", { dbhCm: "28" }); await sync.flush();
  assert.equal(writes, 1);
  assert.equal(sync.snapshot.syncState, "saved");
});

test("edits survive a failed save and remount, then retry only edited fields", async () => {
  const local = cache();
  const read = () => Response.json({ measures: { Tree_001: row("24") }, storage: "cosmos" });
  const first = new FieldMeasureSync("scan", local, async(_url, init)=>init?.method === "PATCH" ? new Response(null,{status:503}) : read());
  await first.load(); first.update("Tree_001", { note: "new note" }); await first.flush();
  assert.equal(first.snapshot.syncState, "error");
  let changes: object | null = null;
  const second = new FieldMeasureSync("scan", local, async(_url, init)=>{
    if (init?.method === "PATCH") {
      changes = JSON.parse(String(init.body)).changes;
      return Response.json({ measures: { Tree_001: { ...row("30"), note: "new note" } }, storage: "cosmos" });
    }
    return read();
  });
  await second.flush();
  assert.deepEqual(changes, { note: "new note" });
  assert.equal(second.snapshot.measures.Tree_001.dbhCm, "30");
  assert.equal(second.snapshot.syncState, "saved");
});

test("edits arriving during an in-flight save are saved afterward without old responses overwriting them", async () => {
  const firstWrite = deferred<Response>();
  const writeStarted = deferred<boolean>();
  const patches: Array<Record<string,string>> = [];
  const sync = new FieldMeasureSync("scan", cache(), async(_url, init)=>{
    if (init?.method !== "PATCH") return Response.json({ measures: { Tree_001: row("24") }, storage: "cosmos" });
    patches.push(JSON.parse(String(init.body)).changes);
    if (patches.length === 1) { writeStarted.resolve(true); return firstWrite.promise; }
    return Response.json({ measures: { Tree_001: { ...row("28"), note: "latest" } }, storage: "cosmos" });
  });
  await sync.load(); sync.update("Tree_001", { dbhCm: "26" });
  const saving = sync.flush(); await writeStarted.promise;
  sync.update("Tree_001", { dbhCm: "28", note: "latest" });
  firstWrite.resolve(Response.json({ measures: { Tree_001: row("26") }, storage: "cosmos" }));
  await saving;
  assert.deepEqual(patches, [{ dbhCm: "26" }, { dbhCm: "28", note: "latest" }]);
  assert.equal(sync.snapshot.measures.Tree_001.dbhCm, "28");
  assert.equal(sync.snapshot.syncState, "saved");
});

test("initial connection failure can be retried and never reports saved before server acknowledgement", async () => {
  let online = false;
  const sync = new FieldMeasureSync("scan", cache(), async(_url, init)=>{
    if (!online) return new Response(null,{status:401});
    return Response.json({ measures: { Tree_001: row(init?.method === "PATCH" ? "28" : "24") }, storage: "cosmos" });
  });
  sync.update("Tree_001", { dbhCm: "28" });
  await sync.flush();
  assert.equal(sync.snapshot.syncState, "error");
  assert.match(sync.snapshot.error, /重新登入/);
  online = true; await sync.flush();
  assert.equal(sync.snapshot.syncState, "saved");
  assert.equal(sync.snapshot.measures.Tree_001.dbhCm, "28");
});
