import assert from "node:assert/strict";
import test from "node:test";
import { selectPipeline } from "../server/importApiPlugin.ts";

test("import uses clearly labelled preview pipeline by default", () => {
  const selected = selectPipeline("/app", "/job", "scan", "path", {});
  assert.equal(selected.mode, "preview");
  assert.match(selected.script, /compute-inventory\.mjs$/);
  assert.deepEqual(selected.args, ["/job", "scan", "path"]);
});

test("configured Arbor3D command selects the official adapter", () => {
  const selected = selectPipeline("/app", "/job", "scan", "path", {
    ARBOR3D_CMD: "python official.py",
  });
  assert.equal(selected.mode, "arbor3d");
  assert.match(selected.script, /run-postprocess\.mjs$/);
  assert.deepEqual(selected.args, ["/job", "scan", "path"]);
});
