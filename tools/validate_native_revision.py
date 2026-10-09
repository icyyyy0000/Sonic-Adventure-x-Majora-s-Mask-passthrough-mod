"""Run native game tests sequentially; never mix two publishers in the live mapping."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    names=['test_roster_polish_live','test_native_physics_live','test_sonic_pause_live','test_sonic_native_live','test_sonic_bumps_live','test_sonic_slopes_live','test_native_wall_live','test_selection_recovery_live']
    ap=argparse.ArgumentParser();ap.add_argument('--sadx',type=Path,required=True);ap.add_argument('--start',choices=names,default=names[0]);args=ap.parse_args()
    for name in names[names.index(args.start):]:
        processes=subprocess.check_output(['tasklist','/fo','csv'],text=True).lower()
        assert '"sonic.exe"' not in processes and '"zelda64recompiled.exe"' not in processes,'Close user games before isolated native tests.'
        print('Checking '+name,flush=True)
        subprocess.run([sys.executable,str(ROOT/'tests'/(name+'.py')),'--sadx',str(args.sadx)],check=True)
        if name=='test_native_physics_live':
            log=(args.sadx/'mods/TerminaAdventureBridge/bridge.log').read_text()
            tones={str(i):[] for i in range(1,7)}
            for char,tone in re.findall(r'Native audio: char=(\d+) tone=(\d+)',log):
                if char in tones and int(tone) not in tones[char]:tones[char].append(int(tone))
            assert all(tones.values()),('Missing native audio events',tones)
            (ROOT/'docs/native-audio-0.1.21.log').write_text(log)
            (ROOT/'docs/native-audio-0.1.21.json').write_text(json.dumps({'version':'0.1.21','status':'passed',
                'tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),
                'character_tones':tones,'effects_implementation_unchanged_since_0_1_10':False,'stage_music_muted':True,
                'user_confirmed_audible_on_0_1_10':True,'method':'Original character task queue capture; user found SADX volume muted and confirmed sounds work.'},indent=2)+'\n')
    print('PASS native revision checks',flush=True)
if __name__=='__main__':main()
