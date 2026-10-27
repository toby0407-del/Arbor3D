import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
if(!fs.existsSync(path.join(root,"dist/index.html"))||!fs.existsSync(path.join(root,"dist-server/productionServer.js"))){
  console.error("Please run npm ci and npm run build in app/ first.");process.exit(1);
}
const env={...process.env,HOST:"127.0.0.1",PORT:process.env.PORT||"5324"};
console.log(`Arbor3D: http://127.0.0.1:${env.PORT}/ (uses app/.env.local Microsoft settings)`);
const child=spawn(process.execPath,["dist-server/productionServer.js"],{cwd:root,env,stdio:"inherit",windowsHide:true});
child.on("error",e=>{console.error(e.message);process.exitCode=1;});
child.on("exit",code=>{process.exitCode=code??1;});
process.on("SIGINT",()=>child.kill("SIGINT"));
process.on("SIGTERM",()=>child.kill("SIGTERM"));
