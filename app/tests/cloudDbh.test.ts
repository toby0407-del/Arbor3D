import assert from "node:assert/strict";
import test from "node:test";
import { validateCloudEndpoint, validateCloudResult } from "../scripts/cloud-dbh-client.mjs";
import { cloudComputeStatus } from "../server/cloudComputeStatus.ts";

test("cloud results require actual full computation and a downloadable checksummed artifact", () => {
  const full = { status: "succeeded", prepare_only: false, execution: { mode: "full", pipeline: "arbor3d" }, result: { sha256: "a".repeat(64), bytes: 100 } };
  assert.doesNotThrow(()=>validateCloudResult(full));
  for (const status of [{...full,prepare_only:true}, {...full,result:null}, {...full,execution:{mode:"prepare"}}, {...full,result:{sha256:"invalid",bytes:100}}]) {
    assert.throws(()=>validateCloudResult(status));
  }
});

test("section-only Azure capability is reported as hybrid, never as full cloud measurement", async () => {
  const state = await cloudComputeStatus({ ARBOR3D_SECTION_CLOUD_URL: "https://cloud.example.test", ARBOR3D_CLOUD_DBH_API_KEY: "private-test-key" }, async(_url, options)=>{
    assert.equal((options?.headers as Record<string,string>)["X-API-Key"], "private-test-key");
    return Response.json({ section_geometry_ready: true, full_pipeline_ready: false, prepare_only: true });
  });
  assert.equal(state.state, "hybrid_ready");
  assert.doesNotMatch(JSON.stringify(state), /private-test-key/);
});

test("remote compute requires encrypted transport and server-side authentication", () => {
  assert.equal(validateCloudEndpoint("https://compute.example.test/", "server-key"), "https://compute.example.test");
  assert.equal(validateCloudEndpoint("http://127.0.0.1:8080", ""), "http://127.0.0.1:8080");
  for (const [url,key] of [["http://compute.example.test","key"],["https://compute.example.test",""],["https://user:key@compute.example.test","key"]]) assert.throws(()=>validateCloudEndpoint(url,key));
});
