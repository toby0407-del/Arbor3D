import assert from 'node:assert/strict';
import test from 'node:test';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import ExcelJS from 'exceljs';
for (const simulated of [false, true]) test(`Excel export preserves every canonical cell, identifier and blank (${simulated ? 'simulated' : 'observed'})`,async()=>{
  const dir=await mkdtemp(join(tmpdir(),'arbor-excel-'));
  try {
    const args = simulated ? ['-m','analytics.simulate','--out',dir] : ['-m','analytics','--report','app/src/data/inventories/20260818092855.json','--site-id','fengchia','--out',dir];
    execFileSync(process.env.ARBOR_PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),['-X','utf8',...args],{cwd:'..'});
    const input=join(dir,simulated ? 'analytics/analytics.json' : 'analytics.json');
    const data=JSON.parse(await readFile(input,'utf8'));
    // A literal formula-like source must remain text, never become an Excel formula.
    data.tables.DimScan[0].source_file='=1+1';
    await writeFile(input,JSON.stringify(data));
    const output=join(dir,'analytics.xlsx');
    execFileSync(process.execPath,['scripts/export-analytics-excel.mjs',input,output]);
    const wb=new ExcelJS.Workbook(); await wb.xlsx.readFile(output);
    for(const [name,rows] of Object.entries(data.tables) as [string,Record<string,unknown>[]][]) {
      if(!rows.length) continue;
      const sheet=wb.getWorksheet(name)!;
      assert.equal(sheet.rowCount,rows.length+1);
      rows.forEach((row,i)=>Object.entries(row).forEach(([,expected],j)=>{
        const got=sheet.getCell(i+2,j+1).value;
        assert.equal(got,expected);
      }));
    }
    assert.equal(wb.getWorksheet('DimScan')!.getCell('C2').type,ExcelJS.ValueType.String);
    assert.equal(wb.getWorksheet('DimScan')!.getCell('E2').value,'=1+1');
    assert.equal(wb.getWorksheet('Overview')!.getCell('B3').value,simulated ? 256 : 16);
    assert.equal(String(wb.getWorksheet('Overview')!.getCell('B1').value).includes('DEMO ONLY'),simulated);
  } finally { await rm(dir,{recursive:true,force:true}); }
});
