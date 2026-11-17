import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const base = process.argv[2] || 'http://127.0.0.1:8080';
const write = process.argv.includes('--write');
let cookie = '';
async function request(route, options = {}) {
  const res = await fetch(`${base}${route}`, {
    ...options,
    headers: { ...options.headers, ...(cookie ? { cookie } : {}) },
    signal: AbortSignal.timeout(20_000),
  });
  assert.equal(res.status, 200, `${route}: ${res.status} ${await res.clone().text()}`);
  return res;
}
async function json(route, options) { return (await request(route, options)).json(); }

assert.equal((await json('/healthz')).ok, true);
assert.match(await (await request('/')).text(), /<div id="root"><\/div>/);
const inventory = (await json('/api/inventories/20260818092855')).report;
assert.ok(inventory.trees.length > 0);
await request('/scans/20260818092855/inventory.json');
const photo = inventory.trees.find(t => t.Best_Photo)?.Best_Photo;
if (photo) await request(`/scans/20260818092855/${photo}`);
const accounts = await json('/api/auth/accounts');
assert.equal(accounts.demo, true, 'Smoke test expects local demo configuration');
const login = await request('/api/auth/demo-login', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ workId: accounts.accounts[0].workId }),
});
cookie = login.headers.get('set-cookie').split(';')[0];
assert.equal((await json('/api/auth/me')).workId, accounts.accounts[0].workId);
const assistant = await json('/api/assistant', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: '胸徑精度要如何複核？', context: {
    parkName: 'Docker smoke test', pathName: 'demo', scanId: '20260818092855', createdAt: '',
    summary: { total: 1, reliable: 0, pending: 1, review: 0, co2Ton: 0 },
    trees: [{ id: 'T001', dbhCm: 20, heightM: null, co2Ton: null, status: 'yellow',
      reviewReason: '待複核', confidence: null, manualDbhCm: null }],
  } }),
});
assert.equal(assistant.provider, 'local');
assert.equal(assistant.ragQuestionCount, 1000);
assert.ok(assistant.answer.length > 0);
assert.ok(assistant.ragSources?.length > 0, 'RAG corpus must be present in runtime image');

if (write) {
  // Writes isolated test records only, never replaces a real survey.
  const scanId = `sim-docker-smoke-${Date.now()}`;
  const measures = { T001: { strict13m: true, dbhCm: '20', note: 'Docker smoke test',
    heightM: '5', coeff: '0.5', measuredAt: '2026-10-03' } };
  await json(`/api/field-measures?scanId=${scanId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ measures }),
  });
  assert.deepEqual((await json(`/api/field-measures?scanId=${scanId}`)).measures, measures);
  const form = new FormData();
  form.append('scanId', scanId);
  form.append('parkName', 'Docker smoke test');
  const sample = await readFile(new URL('../app/public/scans/sim20260315thu001/simulated-demo/tree-demo.ply', import.meta.url));
  form.append('denoised', new Blob([sample]), 'tree.ply');
  form.append('gaussian', new Blob([sample]), 'gaussian.ply');
  // Receiving stage does not decode the JPEG; this tests multipart persistence.
  form.append('rawGo', new Blob([new Uint8Array([255, 216, 255, 217])]), 'test.jpg');
  const uploaded = await json('/api/import/jobs', { method: 'POST', body: form });
  assert.equal(uploaded.job.status, 'queued');
  assert.equal(uploaded.job.fileCounts.denoised, 1);
  assert.equal((await json(`/api/import/jobs/${uploaded.job.id}`)).job.scanId, scanId);
  console.log(JSON.stringify({ persistedTestScan: scanId, uploadedJob: uploaded.job.id }));
}
console.log('PASS: health, production page, inventory media, demo session, local RAG' +
  (write ? ', field-measure persistence, multipart upload' : ''));
