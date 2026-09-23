import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { sessionAccountFromClaims } from "../server/accountApiPlugin.ts";
import { createFieldMeasureStore } from "../server/fieldMeasureStore.ts";

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
