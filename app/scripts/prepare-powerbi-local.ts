// Read current App inputs and synchronized measurements; never change observations.
import { createHash } from 'node:crypto';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { createFieldMeasureStore } from '../server/fieldMeasureStore.js';
import { analyticsInput } from '../src/lib/analytics.js';
import { analyticsFingerprintText } from '../src/lib/localPowerBi.js';
import type { ParkInventoryReport } from '../src/types.js';

const appRoot = process.cwd();
try { process.loadEnvFile(path.join(appRoot, '.env.local')); } catch (e) { if ((e as NodeJS.ErrnoException).code !== 'ENOENT') throw e; }
if (process.env.ARBOR_AZURE_CLI_DIR) process.env.PATH = `${process.env.ARBOR_AZURE_CLI_DIR}${path.delimiter}${process.env.PATH ?? ''}`;
const output = path.resolve(process.argv[2] || '../outputs/powerbi-local/input');
const store = createFieldMeasureStore(appRoot, process.env);
const manifest = JSON.parse(await fs.readFile(path.join(appRoot, 'scenarios/parks/manifest.json'), 'utf8'));
const scans: string[] = ['20260818092855', ...manifest.sites.map((s: {scanId: string}) => s.scanId)];
await fs.mkdir(output, {recursive:true});
const entries = [];
for (const scan of scans) {
  const published = path.join(appRoot, `public/scans/${scan}/inventory.json`);
  const source = await fs.stat(published).catch(()=>null) ? published : path.join(appRoot, `src/data/inventories/${scan}.json`);
  const report = JSON.parse(await fs.readFile(source, 'utf8')) as ParkInventoryReport;
  const measures = await store.read(scan);
  const bundle = analyticsInput(report, measures);
  const fingerprint = createHash('sha256').update(analyticsFingerprintText(report,measures)).digest('hex');
  await fs.writeFile(path.join(output, `${scan}.json`), JSON.stringify(bundle, null, 2));
  entries.push({scan_id:scan, fingerprint, dataset_kind:report.dataset_kind || 'observed'});
}
await fs.writeFile(path.join(output, 'index.json'), JSON.stringify({prepared_at:new Date().toISOString(), entries}, null, 2));
console.log(`Prepared ${entries.length} current App snapshots from ${store.provider}.`);
