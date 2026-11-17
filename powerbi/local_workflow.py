"""Two-step local Desktop refresh and App snapshot update; no Power BI cloud calls."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from powerbi.local_app import prepare, publish
from powerbi.local_history import prepare as prepare_history, verify as verify_history

ROOT = Path(__file__).resolve().parents[1]
POINTER = ROOT / 'outputs/powerbi-local/active.json'


def run_prepare(open_projects=True):
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    root = ROOT / 'outputs/powerbi-local' / stamp
    node = shutil.which('node')
    if not node:
        raise ValueError('Node.js is required')
    subprocess.run([node,'--import','tsx','scripts/prepare-powerbi-local.ts',str(root/'input')], cwd=ROOT/'app', check=True)
    prepare(root/'input',root/'projects')
    prepare_history(root/'projects'/'quarterly')
    POINTER.write_text(json.dumps({'folder':str(root/'projects')},indent=2),encoding='utf-8')
    for kind in ('observed','simulated','quarterly'):
        project = root/'projects'/kind/'powerbi/Arbor3D.pbip'
        print(str(project))
        if open_projects and os.name == 'nt':
            os.startfile(project)
    print('Refresh all three local Desktop projects, then run the App update shortcut. No sign-in needed.')


def desktop_ports():
    result = subprocess.run(['powershell','-NoProfile','-Command',
        "@(Get-CimInstance Win32_Process -Filter \"name='msmdsrv.exe'\" | Select-Object -ExpandProperty CommandLine) | ConvertTo-Json -Compress"],
        capture_output=True,encoding='utf-8',check=True)
    commands = json.loads(result.stdout or '[]')
    if isinstance(commands,str): commands=[commands]
    ports=set()
    for command in commands:
        match=re.search(r'-s\s+"([^"]+)"',command)
        if not match: continue
        portfile=Path(match[1])/'msmdsrv.port.txt'
        if portfile.is_file():
            port=int(portfile.read_text(encoding='utf-16-le').strip('\ufeff\x00\r\n '))
            if 1<=port<=65535: ports.add(port)
    return sorted(ports)


def run_publish():
    active=json.loads(POINTER.read_text(encoding='utf-8'))
    folder=Path(active['folder']).resolve()
    expected_root=(ROOT/'outputs/powerbi-local').resolve()
    if expected_root not in folder.parents:
        raise ValueError('Active project must be inside outputs/powerbi-local')
    candidates=[]
    for port in desktop_ports():
        target=folder/f'desktop-{port}.json'
        result=subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'scripts/export-powerbi-desktop.ps1'),
            '-Port',str(port),'-Output',str(target)],capture_output=True,encoding='utf-8')
        if result.returncode==0: candidates.append(target)
    if not candidates: raise ValueError('Open and refresh the Arbor3D Desktop projects first')
    completed=[]
    for kind in ('observed','simulated'):
        for target in candidates:
            try:
                updated=publish(folder/kind,target,ROOT/'app/public')
            except (ValueError,KeyError,TypeError):
                continue
            completed.extend(updated)
            # A running production App serves dist; update its data without rebuilding code.
            for scan in updated:
                source=ROOT/f'app/public/analysis/{scan}.json'
                if (ROOT/'app/dist').is_dir():
                    destination=ROOT/f'app/dist/analysis/{scan}.json'
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    temporary=destination.with_suffix('.tmp')
                    shutil.copyfile(source,temporary)
                    temporary.replace(destination)
            break
        else:
            raise ValueError(f'{kind}: model not refreshed or inputs changed; no matching Desktop result')
    quarterly=Path(active.get('quarterly_folder',str(folder/'quarterly'))).resolve()
    if expected_root not in quarterly.parents: raise ValueError('Quarterly project must be inside outputs/powerbi-local')
    if quarterly.is_dir():
        for target in candidates:
            try: result=verify_history(quarterly,target)
            except (ValueError,KeyError,TypeError): continue
            print(f"Quarterly Desktop verified: {result['observations']} records.")
            break
        else: raise ValueError('Quarterly project must also be refreshed')
    print(f'Updated {len(completed)} App snapshots. Click Read updated results in the App.')


if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr): stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','publish'])
    parser.add_argument('--no-open',action='store_true',help='Prepare without launching Desktop')
    args=parser.parse_args()
    try:
        run_prepare(not args.no_open) if args.action=='prepare' else run_publish()
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print(f'Local Power BI update stopped: {exc}',file=sys.stderr)
        raise SystemExit(1)
