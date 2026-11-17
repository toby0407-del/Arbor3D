import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
try { process.loadEnvFile(path.join(root,'.env.local')); } catch(error) { if(error.code!=='ENOENT')throw error; }
if(!fs.existsSync(path.join(root,"dist/index.html"))||!fs.existsSync(path.join(root,"dist-server/productionServer.js"))){
  console.error("Please run npm ci and npm run build in app/ first.");process.exit(1);
}
const env={...process.env,HOST:"127.0.0.1",PORT:process.env.PORT||"5324"};
let modelChild=null;
async function startModelIfNeeded(){
  if(env.ARBOR_AI_PROVIDER!=='phi4'||env.ARBOR_MODEL_AUTOSTART==='NO'||!env.FOUNDRY_LOCAL_ENDPOINT)return;
  const endpoint=new URL(env.FOUNDRY_LOCAL_ENDPOINT);
  if(!['localhost','127.0.0.1'].includes(endpoint.hostname))return;
  try {const response=await fetch(new URL('/v1/models',endpoint),{signal:AbortSignal.timeout(2000)});if(response.ok)return;}catch{ /* Start the existing local SDK below. */ }
  const python=path.join(process.env.USERPROFILE||process.env.HOME||'', '.cache/arbor3d/foundry-venv/Scripts/python.exe');
  if(!fs.existsSync(python)){console.error('Start the Microsoft model with the existing model launcher.');return;}
  modelChild=spawn(python,['-u',path.resolve(root,'../scripts/run_foundry_local.py'),'--model','phi-4-mini','--port',endpoint.port||'5273'],{cwd:path.resolve(root,'..'),env,stdio:'inherit',windowsHide:true});
  modelChild.on('error',error=>console.error(`Microsoft model startup failed: ${error.message}`));
  console.log('Starting installed Microsoft Phi-4. The App will show readiness after model loading.');
}
void startModelIfNeeded();
console.log(`Arbor3D: http://127.0.0.1:${env.PORT}/ (uses app/.env.local Microsoft settings)`);
const child=spawn(process.execPath,["dist-server/productionServer.js"],{cwd:root,env,stdio:"inherit",windowsHide:true});
child.on("error",e=>{console.error(e.message);process.exitCode=1;});
child.on("exit",code=>{modelChild?.kill();process.exitCode=code??1;});
process.on("SIGINT",()=>{child.kill("SIGINT");modelChild?.kill();});
process.on("SIGTERM",()=>{child.kill("SIGTERM");modelChild?.kill();});
