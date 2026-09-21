// Portable application export: CSV and Excel consume the same analytics.json snapshot.
import ExcelJS from 'exceljs';
import { readFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
const [input, output] = process.argv.slice(2);
if (!input || !output) throw new Error('Usage: node app/scripts/export-analytics-excel.mjs analytics.json analytics.xlsx');
const data = JSON.parse(await readFile(input, 'utf8'));
if (data.schema_version !== '1.0') throw new Error('Unsupported analytics schema');
const book = new ExcelJS.Workbook();
book.creator = 'Arbor3D';
const summary = book.addWorksheet('Overview');
summary.columns = [{width: 30}, {width: 90}];
summary.addRows([
  ['Arbor3D Analytics', '資料快照；更新資料後重新執行匯出'],
  ['來源', input],
  ['觀測筆數', data.tables.Summary[0].observations],
  ['有效實測配對', data.tables.Summary[0].paired_count],
  ['MAE (cm)', data.tables.Summary[0].mae_cm ?? '無有效配對'],
  ['RMSE (cm)', data.tables.Summary[0].rmse_cm ?? '無有效配對'],
  ['Bias (cm)', data.tables.Summary[0].bias_cm ?? '無有效配對'],
  ['MAPE (%)', data.tables.Summary[0].mape_pct ?? '無有效配對'],
  ['待複核', data.tables.Summary[0].review_count],
  ['来源定義', 'measured=人工實測；ai=演算法；estimated=公式推估；missing=缺值'],
  ['跨期規則', '僅人工確認的固定 Tree ID；同來源、同方法、標準 1.3 m。負增量需複核。'],
  ['碳量限制', '沿用盤點公式的推估 CO₂ 當量，非經查證減碳量或碳權。'],
]);
for (const [name, rows] of Object.entries(data.tables)) {
  const sheet = book.addWorksheet(name);
  if (!rows.length) { sheet.addRow(['無可用資料；不以 0 代替缺測']); sheet.getColumn(1).width = 60; continue; }
  const fields = Object.keys(rows[0]);
  sheet.columns = fields.map(key => ({header: key, key, width: key.endsWith("_key") || key === "scope" ? 66 : key.startsWith("source_") ? 72 : Math.max(18, Math.min(38, key.length + 4))}));
  rows.forEach(row => sheet.addRow(row));
  sheet.autoFilter = {from: {row: 1, column: 1}, to: {row: rows.length + 1, column: fields.length}};
  sheet.views = [{state: 'frozen', ySplit: 1}];
  sheet.eachRow((row, index) => {
    row.height = index === 1 ? 42 : 46;
    row.alignment = {vertical: 'middle', wrapText: true};
    row.eachCell(cell => { if (typeof cell.value === 'string') cell.numFmt = '@';
      if (typeof cell.value === 'number') cell.numFmt = fields[cell.col-1] === 'coefficient' ? '0.0000' : ['observations','paired_count','review_count','days'].includes(fields[cell.col-1]) ? '0' : '0.000'; });
  });
}
summary.eachRow(row => { row.height = 30; row.alignment = {vertical: "middle", wrapText: true}; });
for (const sheet of book.worksheets) {
  sheet.getRow(1).font = {bold: true, color: {argb: 'FFFFFFFF'}};
  sheet.getRow(1).fill = {type: 'pattern', pattern: 'solid', fgColor: {argb: 'FF145A4A'}};
}
await mkdir(dirname(output), {recursive: true});
await book.xlsx.writeFile(output);
console.log(output);
