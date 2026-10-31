import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';

test('updated Desktop snapshots replace cached data; offline uses the latest, HTTP errors stay errors',async()=>{
  const handlers:Record<string,(event:unknown)=>void>={};
  const entries=new Map<string,Response>();
  const cache={put:async(key:string,response:Response)=>{entries.set(key,response);},match:async(key:string)=>entries.get(key)?.clone()};
  let mode='fresh';
  runInNewContext(await readFile(new URL('../public/sw.js',import.meta.url),'utf8'),{
    URL, self:{location:{origin:'http://localhost'},addEventListener:(name:string,handler:(event:unknown)=>void)=>{handlers[name]=handler;}},
    caches:{open:async()=>cache},
    fetch:async()=>{if(mode==='offline')throw new Error('offline');return new Response(mode==='missing'?'missing':'new',{status:mode==='missing'?404:200});},
  });
  entries.set('http://localhost/analysis/s.json',new Response('old'));
  async function request(){
    let result:Promise<Response>|undefined;
    handlers.fetch({request:{url:'http://localhost/analysis/s.json?t=123',method:'GET'},respondWith:(value:Promise<Response>)=>{result=value;}});
    return await result!;
  }
  assert.equal(await (await request()).text(),'new');
  mode='offline'; assert.equal(await (await request()).text(),'new');
  mode='missing'; assert.equal((await request()).status,404);
});
