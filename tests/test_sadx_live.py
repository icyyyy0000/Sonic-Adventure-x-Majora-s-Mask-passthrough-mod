"""Test the installed original SADX engine and companion through their real IPC.

Does not inject Windows input or operate a GUI. Requests character changes using
the companion protocol; restores the temporary inactive-window pause setting.
"""
import argparse
import ctypes as c
import json
import subprocess
import time
from pathlib import Path
from test_transport import Host, Guest
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sadx',type=Path,required=True);args=parser.parse_args()
    game=args.sadx
    profile=game/'mods/.modloader/profiles/Default.json'
    original=profile.read_bytes();config=json.loads(original)
    assert 'TerminaAdventureBridge' in config['EnabledMods']
    config['Graphics']['EnablePauseOnInactive']=False
    dll=c.CDLL(str(ROOT/'build/native/termina_bridge.dll'))
    dll.ta_transport_write_host.argtypes=[c.POINTER(Host)]
    dll.ta_transport_read_guest.argtypes=[c.POINTER(Guest)]
    process=None;results=[]
    try:
        profile.write_text(json.dumps(config,indent=2)+'\n')
        process=subprocess.Popen([str(game/'sonic.exe'),'--level','stationsquare','--act','0','--character','sonic'],cwd=game)
        host=Host(scene=1,epoch=1,flags=1,character=1);guest=Guest()
        for character,name in [(1,'Sonic'),(3,'Knuckles'),(2,'Tails'),(4,'Amy'),(5,'Big'),(6,'E-102 Gamma'),(1,'Sonic return')]:
            host.character=character
            deadline=time.monotonic()+25
            matched=False
            while time.monotonic()<deadline:
                if process.poll() is not None: raise RuntimeError(f'SADX exited with {process.returncode}')
                host.frame+=1;dll.ta_transport_write_host(c.byref(host))
                if dll.ta_transport_read_guest(c.byref(guest)) and guest.character==character and guest.flags&2:
                    matched=True;break
                time.sleep(.05)
            results.append({'character':name,'matched':matched,'native_action':guest.action if matched else None})
            if not matched: raise RuntimeError(f'Original {name} task did not match before the timeout')
            # Continue checking a few frames after a swap, not just one stale snapshot.
            first=guest.frame;end=time.monotonic()+.4
            while time.monotonic()<end:
                host.frame+=1;dll.ta_transport_write_host(c.byref(host));time.sleep(.05)
            assert dll.ta_transport_read_guest(c.byref(guest)) and guest.frame>first and guest.character==character
            print(f'PASS: original {name} task matched and continued updating',flush=True)
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        profile.write_bytes(original)
        (ROOT/'docs/sadx-live-test.json').write_text(json.dumps({'checks':results,'profile_restored':True,
            'method':'Original SADX process plus companion IPC; no Windows input injection',
            'zelda_gameplay_verified':False,'world_takeover_active':False},indent=2)+'\n')
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
