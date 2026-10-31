// Explicit integration probe. A unique non-observation partition is removed in finally.
import { randomUUID } from "node:crypto";
import path from "node:path";
import assert from "node:assert/strict";
import { CosmosClient } from "@azure/cosmos";
import { AzureCliCredential } from "@azure/identity";

process.loadEnvFile(".env.local");
if (!process.env.AZURE_COSMOS_ENDPOINT) throw new Error("Cosmos is not configured");
if (process.env.ARBOR_AZURE_CLI_DIR) process.env.PATH = `${process.env.ARBOR_AZURE_CLI_DIR}${path.delimiter}${process.env.PATH ?? ""}`;
const base = "http://127.0.0.1:5324";
const scanId = `connection-verification-${randomUUID()}`;
const marker = `DISPOSABLE CONNECTION TEST ${scanId}`;
const url = `${base}/api/field-measures?scanId=${scanId}`;
const client = new CosmosClient({ endpoint: process.env.AZURE_COSMOS_ENDPOINT, aadCredentials: new AzureCliCredential() });
const container = client.database(process.env.AZURE_COSMOS_DATABASE || "Arbor3D").container(process.env.AZURE_COSMOS_CONTAINER || "FieldMeasures");
const login = await fetch(`${base}/api/auth/demo-login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workId: "E-1027" }) });
assert.equal(login.status, 200);
const cookie = login.headers.get("set-cookie")?.split(";")[0];
assert.ok(cookie);
const headers = { cookie, "Content-Type": "application/json" };
try {
  assert.equal((await fetch(url)).status, 401);
  const patches = [
    { treeId: "ConnectionProbe", changes: { note: marker } },
    { treeId: "ConnectionProbe", changes: { strict13m: false } },
    { treeId: "ConnectionProbe2", changes: { note: marker } },
  ];
  const results = await Promise.all(patches.map(body=>fetch(url,{ method: "PATCH", headers, body: JSON.stringify(body) })));
  for (const response of results) assert.equal(response.status, 200, await response.text());
  const read = await fetch(url, { headers }).then(r=>r.json());
  assert.equal(read.storage, "cosmos");
  assert.equal(read.measures.ConnectionProbe.note, marker);
  assert.equal(read.measures.ConnectionProbe.strict13m, false);
  assert.equal(read.measures.ConnectionProbe2.note, marker);
  assert.equal(read.measures.ConnectionProbe.dbhCm, "");
  assert.equal((await fetch(url,{method:"PATCH",headers,body:JSON.stringify({treeId:"ConnectionProbe",changes:{updatedBy:"invalid"}})})).status,400);
  console.log(JSON.stringify({ cosmos: true, concurrentFieldUpdates: true, readBack: true, authenticationRequired: true, invalidPatchRejected: true }));
} finally {
  try {
    const item = container.item(`field-measures:${scanId}`, scanId);
    const { resource } = await item.read<{ id: string; scanId: string }>();
    if (resource?.scanId === scanId && resource.id === `field-measures:${scanId}`) {
      await item.delete();
      console.log("Disposable connection probe removed; no observed tree records changed.");
    }
  } finally {
    await fetch(`${base}/api/auth/logout`, { method: "POST", headers });
    client.dispose();
  }
}
