"""Focused original-engine elevated-floor and slope collision check."""
import ctypes as c,time,subprocess,argparse,json,hashlib
from pathlib import Path
from test_transport import Host,Guest
from test_world import World
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sadx',type=Path,required=True);args=ap.parse_args()
    dll=c.CDLL(str(ROOT/'build/native/termina_bridge.dll'))
    dll.ta_transport_write_host.argtypes=[c.POINTER(Host)];dll.ta_transport_write_world.argtypes=[c.POINTER(World)];dll.ta_transport_read_guest.argtypes=[c.POINTER(Guest)]
    host=Host(scene=17,epoch=300,character=1,flags=3);host.position[:]=[100,100,0]
    world=World(scene=17,epoch=300,count=2,radius=3000)
    world.triangles[0].flags=world.triangles[1].flags=1
    world.triangles[0].vertices[:]=[-3000,20,-3000,3000,20,3000,3000,20,-3000]
    world.triangles[1].vertices[:]=[-3000,20,-3000,-3000,20,3000,3000,20,3000]
    guest=Guest();process=None;results=[];passed=False
    def tick():
        if process.poll() is not None:raise RuntimeError('SADX exited')
        host.frame+=1;world.revision=host.frame
        for fn,packet in [(dll.ta_transport_write_host,host),(dll.ta_transport_write_world,world)]:
            for _ in range(100):
                if fn(c.byref(packet)):break
                time.sleep(.002)
            else:raise RuntimeError('Transport busy')
        time.sleep(.05);dll.ta_transport_read_guest(c.byref(guest))
    try:
        process=subprocess.Popen([str(args.sadx/'sonic.exe'),'--level','stationsquare','--act','0','--character','sonic'],cwd=args.sadx)
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            tick()
            if guest.flags&8 and guest.epoch==host.epoch and guest.status&1:break
        else:raise RuntimeError('Sonic did not load')
        for grade in (.8,1.5,2.5):
            host.epoch+=1;world.epoch=host.epoch;host.position[:]=[0,50,0];host.stickY=host.buttons=0
            for triangle in world.triangles[:2]:
                for i in range(3):triangle.vertices[i*3+1]=triangle.vertices[i*3]*grade
            for _ in range(45):tick()
            worst=0
            def contact(label):
                nonlocal worst
                penetration=guest.position[0]*grade-guest.position[1];worst=max(worst,penetration)
                assert guest.flags&8 and guest.epoch==host.epoch,('lost ownership',label,grade,guest.flags)
                assert penetration<.5,('under slope',label,grade,list(guest.position),guest.status,guest.action)
            contact('settle')
            host.stickY=80
            for _ in range(30):tick();contact('uphill run')
            host.stickY=0;host.buttons=0x4000
            for _ in range(10):tick();contact('charge')
            host.buttons=0
            for _ in range(15):tick();contact('dash uphill')
            host.stickY=-80
            for _ in range(30):tick();contact('downhill turn')
            results.append({'grade':grade,'angle_degrees':round(__import__('math').degrees(__import__('math').atan(grade)),1),'max_penetration':worst,'position':list(guest.position)})
            print('PASS steep ramp',results[-1],flush=True)
        passed=True
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:process.terminate();process.wait(timeout=5)
        (ROOT/'docs/sonic-slopes-0.1.21.json').write_text(json.dumps({'version':'0.1.21','tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),'status':'passed' if passed else 'failed','checks':results,'actual_zelda_slopes_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
