import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(
  new URL("../src/data/scanBindings.ts", import.meta.url),
  "utf8",
);

const bindings = source.match(/parkName: "/g) ?? [];
const emptyRoutes = source.match(/polyline: \[\],/g) ?? [];
const referencedRoutes = source.match(/OSM (?:footway|pedestrian) \d+/g) ?? [];

test("every mapped route has an auditable OSM pedestrian reference", () => {
  assert.equal(bindings.length, 25);
  assert.equal(emptyRoutes.length, 2);
  assert.equal(referencedRoutes.length, bindings.length - emptyRoutes.length);
});

test("unverified campuses do not display guessed straight lines", () => {
  for (const park of ["中山醫學大學", "弘光科技大學"]) {
    const block = source.match(
      new RegExp(`parkName: "${park}"[\\s\\S]*?\\n  \\},`),
    )?.[0];
    assert.ok(block, `${park} binding should exist`);
    assert.match(block, /pathName: "待現場錄製路徑（模擬資料）"/);
    assert.match(block, /polyline: \[\],/);
  }
});
