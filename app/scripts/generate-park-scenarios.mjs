/** Rebuild park-only scenarios from the immutable Feng Chia experiment. */
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = p => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
const templatePath = 'src/data/inventories/20260818092855.json';
const template = read(templatePath);
const sites = read('scripts/park-simulation-sites.json');
const sha = createHash('sha256').update(fs.readFileSync(path.join(root, templatePath))).digest('hex');
const round = (v, n = 2) => Number(v.toFixed(n));
const write = (p, data) => {
  const target = path.join(root, p);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, data, 'utf8');
};
const json = (p, data) => write(p, JSON.stringify(data, null, 2) + '\n');
const allRows = [];
const manifest = [];
for (const [siteIndex, site] of sites.entries()) {
  if (!site.scanId.startsWith('sim') || /大學|學校|高中|國中|國小/.test(site.parkName)) throw Error('Park-only simulations required');
  const seed = 20260923 + siteIndex;
  let state = seed;
  const random = () => ((state = (Math.imul(1664525, state) + 1013904223) >>> 0) / 4294967296);
  const normal = () => Math.sqrt(-2 * Math.log(Math.max(1e-12, random()))) * Math.cos(2 * Math.PI * random());
  const track = site.polyline.length ? site.polyline : Array.from({ length: 9 }, (_, i) => [
    round(site.center[0] + Math.sin(i * Math.PI / 4) * 0.00018, 7),
    round(site.center[1] + Math.cos(i * Math.PI / 4) * 0.00022, 7),
  ]);
  const trees = Array.from({ length: site.trees }, (_, i) => {
    const ref = template.trees[i % template.trees.length];
    const id = `Tree_${String(i + 1).padStart(3, '0')}`;
    const persistent = `SIM-${site.siteId}-${id}`;
    const anchor = (ref.DBH_cm || 30) * (0.85 + random() * 0.3);
    const annual = 0.35 + random() * 0.8;
    const scenario = ['steady', 'slow', 'stalled', 'negative_review'][i % 4];
    const fraction = i / Math.max(1, site.trees - 1) * (track.length - 1);
    const a = Math.min(track.length - 2, Math.floor(fraction));
    const gps = track[a].map((v, axis) => round(v + (track[a + 1][axis] - v) * (fraction - a), 7));
    const quarterly = Array.from({ length: 16 }, (_, q) => {
      const quarterIndex = 2022 * 4 + 2 + q;
      const year = Math.floor(quarterIndex / 4), quarter = quarterIndex % 4 + 1;
      const date = `${year}-${String(quarter * 3).padStart(2, '0')}-${[31, 30, 30, 31][quarter - 1]}`;
      const step = scenario === 'stalled' ? Math.min(q, 8) : q;
      const latent = Math.max(3, anchor - annual * 15 / 4 + annual * step / 4 * (scenario === 'slow' ? 0.25 : 1) - (scenario === 'negative_review' && q >= 13 ? 1.5 : 0));
      const row = {
        dataset_kind: 'simulated', site_id: site.siteId, park_name: site.parkName,
        scan_id: `${site.scanId}-${year}Q${quarter}`, local_tree_id: id, persistent_tree_id: persistent,
        quarter: `${year}Q${quarter}`, date, scenario,
        simulated_manual_dbh_cm: round(latent + normal() * 0.04),
        simulated_ai_dbh_cm: round(latent + 0.12 + normal() * 0.32),
        simulated_height_m: round(1.3 + 1.8 * Math.sqrt(latent)),
        simulated_latitude: gps[0], simulated_longitude: gps[1],
        simulated_measurement_height_m: 1.3, identity_kind: 'simulated', position_kind: 'simulated',
        reference_scan_id: template.scan_id, reference_tree_id: ref.Tree_ID, seed,
      };
      allRows.push(row);
      return row;
    });
    const last = quarterly.at(-1);
    return {
      ...ref, Tree_ID: id, dataset_kind: 'simulated', persistent_tree_id: persistent,
      reference_scan_id: template.scan_id, reference_tree_id: ref.Tree_ID,
      DBH_cm: last.simulated_ai_dbh_cm, previous_DBH_cm: quarterly.at(-2).simulated_ai_dbh_cm,
      DBH_method: 'simulated_circle', DBH_note: `模擬資料,${scenario}`,
      dbh_is_strict_breast_height: true, Height_m: last.simulated_height_m,
      GPS_Location: gps, position_kind: 'simulated',
      Local_XYZ_m: [round((gps[1] - site.center[1]) * 101500, 3), round((gps[0] - site.center[0]) * 111320, 3), 1.3],
      YOLO_confidence: round(Math.max(0.1, Math.min(0.99, (ref.YOLO_confidence || 0.5) + normal() * 0.03)), 4),
      quarterly_observations: quarterly,
    };
  });
  const report = {
    scan_id: site.scanId, created_at: '2026-06-30T10:30:00+08:00', dataset_kind: 'simulated',
    simulation_notice: '四年季度、1.3 m 人工胸徑、樹高、固定樹號、GPS/GPX 與三類技術影像均為合成展示資料，非本公園現場證據。',
    simulation_reference: { scan_id: template.scan_id, sha256: sha, seed },
    gps_available: false, position_kind: 'simulated', num_trees: trees.length, trees,
  };
  json(`src/data/inventories/${site.scanId}.json`, report);
  const gpx = `<?xml version="1.0" encoding="UTF-8"?><gpx version="1.1" creator="Arbor3D SIMULATED" xmlns="http://www.topografix.com/GPX/1/1"><metadata><name>SIMULATED ${site.parkName}</name><desc>合成示範軌跡，非現場 GPS；不可作為導航或現勘證據。</desc></metadata><trk><name>SIMULATED</name><trkseg>${track.map(([lat, lon]) => `<trkpt lat="${lat}" lon="${lon}"/>`).join('')}</trkseg></trk></gpx>`;
  write(`scenarios/parks/${site.scanId}-SIMULATED.gpx`, gpx);
  manifest.push({ ...site, seed, observations: trees.length * 16 });
}
const columns = Object.keys(allRows[0]);
const csv = '\ufeff' + [columns, ...allRows.map(r => columns.map(k => r[k]))].map(r => r.map(v => `"${String(v).replaceAll('"', '""')}"`).join(',')).join('\n') + '\n';
write('scenarios/parks/quarterly-SIMULATED.csv', csv);
json('scenarios/parks/manifest.json', {
  dataset_kind: 'simulated', reference_scan_id: template.scan_id, template_sha256: sha,
  start: '2022-09-30', end: '2026-06-30', quarters: 16, observations: allRows.length, sites: manifest,
  assumptions: ['DBH anchor = FCU source value × U(0.85,1.15); not calibrated truth.',
    'Annual growth U(0.35,1.15) cm; scripted slow/stalled/negative scenarios; not health diagnoses.',
    'Manual noise SD=0.04 cm; AI noise bias=0.12 cm, SD=0.32 cm; assumed, not validated accuracy.',
    'Height = 1.3+1.8*sqrt(latent DBH); no measured height reference.',
    'Identity, 1.3m protocol, GPS and GPX are synthetic. New park tracks are schematic circles, not mapped footways.',
    'FCU images are reference-only; borrowed imagery does not depict simulated measurements.'],
});
await import('./generate-simulated-media.mjs');
console.log(`Generated ${sites.length} park scenarios, ${allRows.length} quarterly observations.`);
