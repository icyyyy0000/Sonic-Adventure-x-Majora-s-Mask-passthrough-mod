"""Install this local revision without resetting settings, saves or enabled mods."""
from pathlib import Path
import json
import shutil
import zipfile
ROOT=Path(__file__).resolve().parents[1]
def main():
    source=ROOT/'build/termina_adventure-0.1.22.nrm'
    with zipfile.ZipFile(source) as z:
        assert z.testzip() is None
        metadata=json.loads(z.read('mod.json'))
        assert metadata['id']=='termina_adventure' and metadata['version']=='0.1.22'
    mods=ROOT/'runtime/mods';mods.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,mods/source.name)
    # Only remove the superseded version of this exact project mod; keep backup.
    backup=ROOT/'build/previous';backup.mkdir(exist_ok=True)
    for version in ['0.1.0','0.1.1','0.1.2','0.1.3','0.1.4','0.1.5','0.1.6','0.1.7','0.1.8','0.1.9','0.1.10','0.1.11','0.1.12','0.1.13','0.1.14','0.1.15','0.1.16','0.1.17','0.1.18','0.1.19','0.1.20','0.1.21']:
        for folder,stem in [(mods,'termina_adventure'),(ROOT/'release/core','termina_adventure'),
                            (mods,'termina_adventure_bridge'),(ROOT/'release/observer/recomp','termina_adventure_bridge')]:
            previous=folder/f'{stem}-{version}.nrm'
            if previous.exists():
                shutil.copy2(previous,backup/previous.name);previous.unlink()
    (ROOT/'Launch with diagnostics.cmd').write_text('@echo off\ncd /d "%~dp0runtime"\nZelda64Recompiled.exe > "%~dp0docs\\game-diagnostics.log" 2>&1\n',encoding='utf-8')
    print('Installed 0.1.22 in the existing portable runtime; settings and saves preserved.')
if __name__=='__main__':main()
