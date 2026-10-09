"""Focused original-engine elevated-floor and slope collision check."""
import ctypes as c,time,subprocess,argparse,json
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
        for kind in ['elevated_floor','raised_again','slope']:
            if kind=='raised_again':
                host.epoch=world.epoch=302
                for triangle in world.triangles[:2]:
                    for i in range(3):triangle.vertices[i*3+1]=60
            if kind=='slope':
                host.epoch=world.epoch=301
                for triangle in world.triangles[:2]:
                    for i in range(3):triangle.vertices[i*3+1]=triangle.vertices[i*3]*.2
            for _ in range(180):tick()
            result={'geometry':kind,'position':list(guest.position),'flags':guest.flags,'epoch':guest.epoch,'status':guest.status,'rotationZ':guest.rotationZ,'offset':guest.modelOffsetY}
            results.append(result);print(result,flush=True)
            expected=20 if kind=='elevated_floor' else 60 if kind=='raised_again' else guest.position[0]*.2
            assert guest.epoch==host.epoch and guest.flags&8 and guest.status&1,result
            assert abs(guest.position[1]-expected)<3,result
        passed=True
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:process.terminate();process.wait(timeout=5)
        (ROOT/'docs/native-geometry-live-test.json').write_text(json.dumps({'status':'passed' if passed else 'failed','checks':results},indent=2)+'\n')
if __name__=='__main__':main()
