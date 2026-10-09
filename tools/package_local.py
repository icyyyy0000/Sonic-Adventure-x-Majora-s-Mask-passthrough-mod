"""Organize local-only build products. Does not include the ROM or game executables."""
import json
import shutil
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    release=ROOT/'release/0.1.22'
    core=release/'core'
    host=release/'observer/recomp'
    guest=release/'observer/sadx/TerminaAdventureBridge'
    for folder in [core,host,guest]:folder.mkdir(parents=True,exist_ok=True)
    artifacts=[(ROOT/'build/termina_adventure-0.1.22.nrm',core),
               (ROOT/'build/termina_adventure_bridge-0.1.22.nrm',host),
               (ROOT/'build/native/termina_bridge.dll',host),
               (ROOT/'build/native/termina_bridge.dll',core),
               (ROOT/'build/native/TerminaAdventureSADX.dll',guest),
               (ROOT/'guest/mod.ini',guest),(ROOT/'guest/config.ini',guest)]
    for path,destination in artifacts:shutil.copy2(path,destination/path.name)
    for path in core.glob('*.nrm'):
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            m=json.loads(z.read('mod.json'))
            assert m['id']=='termina_adventure' and m['version']=='0.1.22'
    with zipfile.ZipFile(host/'termina_adventure_bridge-0.1.22.nrm') as z:
        assert z.testzip() is None
        m=json.loads(z.read('mod.json'))
        assert 'termina_adventure:0.1.22' in m['dependencies']
    (release/'README.txt').write_text('LOCAL DEVELOPMENT BUILD\n\n'
        'core: asset-containing character prototype .nrm; keep local.\n'
        'observer/recomp: companion .nrm and 64-bit DLL, install together.\n'
        'observer/sadx: 32-bit SADX companion mod folder.\n'
        'Installed locally; 0.1.18 collision retained; second-press Tails flight, simulated tail rotor and smaller contextual hints.\n'
        'Controlled native-owner, dense-world, homing safety and transport tests passed; gameplay retest is needed.\n'
        'See ../../README.md and ../../docs/STATUS.md for controls and limitations.\n')
    print(f'Local package organized at {release}')
if __name__=='__main__':main()
