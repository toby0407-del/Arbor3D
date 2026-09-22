import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { quarterlyGrowth } from '../src/lib/growth';

const root = path.resolve(import.meta.dirname, '..');
const read = (p: string) => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
const manifest = read('scenarios/parks/manifest.json');
test('only Feng Chia retains campus routes; new parks have no invented mapped routes', () => {
  const source = fs.readFileSync(path.join(root, 'src/data/scanBindings.ts'), 'utf8');
  const names = [...source.matchAll(/parkName: "([^"]+)"/g)].map(m => m[1]);
  assert.deepEqual(names.filter(n => /大學|學校/.test(n)), ['逢甲大學']);
  assert.equal((source.match(/OSM (?:footway|pedestrian) \d+/g) ?? []).length, 13);
  const extra = read('src/data/extraParkBindings.json');
  assert.equal(extra.length, 6);
  for (const park of extra) assert.deepEqual(park.polyline, []);
});

test('all park scenarios preserve source lineage, identities, 16 quarters and published parity', () => {
  const template = fs.readFileSync(path.join(root, 'src/data/inventories/20260818092855.json'));
  assert.equal(createHash('sha256').update(template).digest('hex'), manifest.template_sha256);
  assert.equal(manifest.sites.length, 18);
  const persistent = new Set();
  let total = 0;
  for (const site of manifest.sites) {
    const report = read(`src/data/inventories/${site.scanId}.json`);
    assert.deepEqual(report, read(`public/scans/${site.scanId}/inventory.json`));
    assert.equal(report.dataset_kind, 'simulated');
    assert.equal(report.gps_available, false);
    for (const tree of report.trees) {
      assert.ok(!persistent.has(tree.persistent_tree_id));
      persistent.add(tree.persistent_tree_id);
      const rows = tree.quarterly_observations;
      assert.equal(rows.length, 16);
      assert.equal(new Set(rows.map((r: {quarter: string}) => r.quarter)).size, 16);
      assert.equal(rows[0].date, '2022-09-30');
      assert.equal(rows.at(-1).date, '2026-06-30');
      assert.equal(tree.DBH_cm, rows.at(-1).simulated_ai_dbh_cm);
      assert.equal(tree.previous_DBH_cm, rows.at(-2).simulated_ai_dbh_cm);
      const growth = quarterlyGrowth(rows);
      assert.equal(growth.current.dbhCm, tree.DBH_cm);
      assert.equal(growth.points.length, 16);
      assert.ok(growth.points.every(p => p.source === 'sim'));
      for (const row of rows) {
        assert.equal(row.dataset_kind, 'simulated');
        assert.equal(row.persistent_tree_id, tree.persistent_tree_id);
        assert.equal(row.reference_tree_id, tree.reference_tree_id);
        assert.equal(row.position_kind, 'simulated');
        assert.ok(row.simulated_manual_dbh_cm > 0 && row.simulated_height_m > 0);
      }
      total += rows.length;
    }
  }
  assert.equal(total, 4720);
  assert.equal(total, manifest.observations);
});
