import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { sessionAccountFromClaims } from "../server/accountApiPlugin.ts";
import { createFieldMeasureStore } from "../server/fieldMeasureStore.ts";
import { validMeasureId, validMeasurePatch } from "../server/fieldMeasurePatch.ts";

test("Microsoft Entra claims become the server session identity and role", () => {
  assert.deepEqual(sessionAccountFromClaims({
    preferred_username: "user@example.gov.tw",
    name: "王小明",
    roles: ["承辦人"],
  }), {
    workId: "user@example.gov.tw",
    name: "王小明",
    role: "承辦人",
  });
});

test("field patches preserve concurrent edits and file storage recovers after a failed save", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "arbor3d-patch-"));
  const audit = { updatedAt: "2026-10-27", updatedBy: "test" };
  try {
    const store = createFieldMeasureStore(root, {});
    await writeFile(path.join(root, ".runtime"), "blocked-directory");
    await assert.rejects(store.patch("scan", "Tree_001", { dbhCm: "24" }, audit));
    await rm(path.join(root, ".runtime"));
    await Promise.all([
      store.patch("scan", "Tree_001", { dbhCm: "24" }, audit),
      store.patch("scan", "Tree_001", { note: "reviewed" }, audit),
      store.patch("scan", "Tree_002", { heightM: "10" }, audit),
    ]);
    const rows = await store.read("scan");
    assert.equal(rows.Tree_001.dbhCm, "24");
    assert.equal(rows.Tree_001.note, "reviewed");
    assert.equal(rows.Tree_002.heightM, "10");
    await store.check();
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("field patch validation rejects unknown fields, oversized values and reserved record IDs", () => {
  assert.equal(validMeasurePatch({ strict13m: true, dbhCm: "24" }), true);
  for (const patch of [{}, { strict13m: "yes" }, { updatedBy: "other" }, { note: "x".repeat(501) }, []]) {
    assert.equal(validMeasurePatch(patch), false);
  }
  for (const id of ["__proto__", "constructor", "../scan", ""]) assert.equal(validMeasureId(id), false);
});

test("field measures use file fallback locally and Cosmos when configured", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "arbor3d-store-"));
  try {
    const local = createFieldMeasureStore(root, {});
    assert.equal(local.provider, "file");
    const measures = {
      Tree_001: {
        strict13m: true,
        dbhCm: "20.5",
        note: "",
        heightM: "8",
        coeff: "",
        measuredAt: "2026-09-23",
      },
    };
    await local.write("scan-1", measures, { updatedAt: "2026-09-23", updatedBy: "tester" });
    assert.deepEqual(await local.read("scan-1"), measures);
    assert.equal(createFieldMeasureStore(root, {
      AZURE_COSMOS_ENDPOINT: "https://example.documents.azure.com:443/",
    }).provider, "cosmos");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
