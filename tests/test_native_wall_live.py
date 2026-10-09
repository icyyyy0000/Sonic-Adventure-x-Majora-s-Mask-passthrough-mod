"""Exercise original SADX character tasks against a deliberately foreign floor.

Only our test game process is stopped; no Windows input is injected.
"""
import ctypes as c
import subprocess,time,json,argparse,hashlib
from pathlib import Path
from test_transport import Host,Guest
from test_world import World
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--sadx',type=Path,required=True);args=p.parse_args()
    dll=c.CDLL(str(ROOT/'build/native/termina_bridge.dll'))
    dll.ta_transport_write_host.argtypes=[c.POINTER(Host)]
    dll.ta_transport_write_world.argtypes=[c.POINTER(World)]
    dll.ta_transport_read_guest.argtypes=[c.POINTER(Guest)]
    host=Host(scene=17,epoch=222,character=1,flags=3)
    host.position[:]=[100,50,170]
    world=World(scene=17,epoch=222,revision=1,count=2,radius=3000)
    # Zelda test floor at y=0, entirely independent of Station Square's terrain.
    world.triangles[0].flags=world.triangles[1].flags=1
    world.triangles[0].vertices[:]=[-3000,0,-3000,3000,0,3000,3000,0,-3000]
    world.triangles[1].vertices[:]=[-3000,0,-3000,-3000,0,3000,3000,0,3000]
    guest=Guest();results=[];process=None;passed=False
    def tick():
        if process.poll() is not None:raise RuntimeError(f'SADX exited {process.returncode}')
        host.frame+=1;world.revision=host.frame
        for function,packet in [(dll.ta_transport_write_host,host),(dll.ta_transport_write_world,world)]:
            deadline=time.monotonic()+.2
            while not function(c.byref(packet)):
                if time.monotonic()>deadline:raise RuntimeError('Transport publication stayed busy')
                time.sleep(.002)
        time.sleep(.05)
        return dll.ta_transport_read_guest(c.byref(guest))
    try:
        process=subprocess.Popen([str(args.sadx/'sonic.exe'),'--level','stationsquare','--act','0','--character','sonic'],cwd=args.sadx)
        host.epoch=world.epoch=224;host.position[:]=[100,100,0]
        for triangle in world.triangles[:2]:
            for i in range(3):triangle.vertices[i*3+1]=triangle.vertices[i*3]*.2
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            if tick() and guest.flags&8 and guest.epoch==host.epoch and guest.status&1:break
        else:raise RuntimeError('Sonic never activated on streamed slope')
        for _ in range(20):tick()
        # A front-facing wall must block native running, rather than the old stage.
        host.epoch=world.epoch=225;host.position[:]=[100,50,0]
        for triangle in world.triangles[:2]:
            for i in range(3): triangle.vertices[i*3+1]=0
        world.count=4
        world.triangles[2].flags=world.triangles[3].flags=1
        world.triangles[2].vertices[:]=[220,-50,-3000,220,300,3000,220,300,-3000]
        world.triangles[3].vertices[:]=[220,-50,-3000,220,-50,3000,220,300,3000]
        for _ in range(45):tick()
        host.stickY=80
        for _ in range(70):tick()
        host.stickY=0
        assert 190<guest.position[0]<220,('Wall collision failed',list(guest.position))
        results.append({'native_wall_blocks_running':'passed','blocked_x':round(guest.position[0],3)})
        print('PASS native task plus swept wall contact',flush=True)
        host.stickX=80;host.stickY=80
        before=list(guest.position)
        for _ in range(25):tick()
        assert abs(guest.position[2]-before[2])>10 and guest.position[0]<220,('Wall slide stuck',list(guest.position),before)
        host.stickX=0;host.stickY=-80;before=list(guest.position)
        for _ in range(35):tick()
        assert guest.position[0]<before[0]-10,('Cannot leave wall',list(guest.position),before)
        results.append({'wall_slide_and_release':'passed'})
        host.character=0;host.flags=0
        for _ in range(5):tick()
        assert not (guest.flags&8),'Native physics did not relinquish Link ownership'
        results.append({'scene_epoch_and_Link_yield':'passed'})
        print('PASS scene epoch and Link yield',flush=True)
        passed=True
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/native-wall-live-test.json').write_text(json.dumps({'version':'0.1.21','tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),'status':'passed' if passed else 'failed','method':'Installed original SADX tasks with streamed collision/contact adapters and synthetic host packets','checks':results,'zelda_gameplay_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
