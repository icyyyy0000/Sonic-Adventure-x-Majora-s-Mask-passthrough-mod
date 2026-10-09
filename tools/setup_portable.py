"""Create an isolated portable copy of the user's installed recomp and local ROM."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED_ROM_SHA1='d6133ace5afaa0882cf214cf88daba39e266c078'
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--recomp',type=Path,required=True)
    p.add_argument('--rom',type=Path,required=True)
    args=p.parse_args()
    if not (args.recomp/'Zelda64Recompiled.exe').is_file():raise SystemExit('Recomp executable not found')
    digest=hashlib.sha1(args.rom.read_bytes()).hexdigest()
    if digest!=EXPECTED_ROM_SHA1:raise SystemExit(f'Expected USA 1.0 big-endian ROM; SHA1 was {digest}')
    runtime=ROOT/'runtime'
    runtime.mkdir(exist_ok=True)
    # Copy only the pre-existing application and its assets; saves stay isolated.
    for filename in ['Zelda64Recompiled.exe','SDL2.dll','dxcompiler.dll','dxil.dll','recompcontrollerdb.txt']:
        shutil.copy2(args.recomp/filename,runtime/filename)
    shutil.copytree(args.recomp/'assets',runtime/'assets',dirs_exist_ok=True)
    shutil.copy2(args.rom,runtime/'mm.n64.us.1.0.z64')
    (runtime/'portable.txt').write_text('Termina Adventure isolated development profile\n')
    mods=runtime/'mods';mods.mkdir(exist_ok=True)
    core=ROOT/'build/termina_adventure-0.1.2.nrm'
    with zipfile.ZipFile(core) as z:
        assert z.testzip() is None
        assert json.loads(z.read('mod.json'))['id']=='termina_adventure'
    shutil.copy2(core,mods/core.name)
    # Observer remains outside the installed mod folder until deliberately tested.
    (runtime/'mods.json').write_text(json.dumps({'enabled_mods':['termina_adventure'],
        'mod_order':['termina_adventure','mm_recomp_dpad_builtin'],'game_mode':''},indent=2))
    launcher=ROOT/'Launch Termina Adventure.cmd'
    launcher.write_text('@echo off\ncd /d "%~dp0runtime"\nstart "Termina Adventure" "Zelda64Recompiled.exe"\n',encoding='utf-8')
    (ROOT/'docs/local-install.json').write_text(json.dumps({'recomp_version':'1.2.2','source_recomp':str(args.recomp),
        'rom_sha1':digest,'portable_runtime':str(runtime),'core_mod_installed':True,
        'observer_installed':False,'existing_save_files_modified':False},indent=2))
    print(f'Portable runtime ready at {runtime}')
if __name__=='__main__':main()
