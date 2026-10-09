"""Original Sonic task over repeated small crests/dips; jump/drop must remain free."""
import argparse,ctypes as c,hashlib,json,math,subprocess,time
from pathlib import Path
from test_transport import Host,Guest
from test_world import World
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sadx',type=Path,required=True);args=ap.parse_args()
    dll=c.CDLL(str(ROOT/'build/native/termina_bridge.dll'))
    dll.ta_transport_write_host.argtypes=[c.POINTER(Host)];dll.ta_transport_write_world.argtypes=[c.POINTER(World)];dll.ta_transport_read_guest.argtypes=[c.POINTER(Guest)]
    host=Host(scene=17,epoch=600,character=1,flags=3);host.position[:]=[0,40,0]
    world=World(scene=17,epoch=600,radius=3000)
    def height(x):return math.sin(x*math.pi/20)*1.5
    segments=list(range(-1000,1600,10));world.count=len(segments)*2
    for index,x in enumerate(segments):
        a=height(x);b=height(x+10)
        for t in world.triangles[index*2:index*2+2]:t.flags=1
        world.triangles[index*2].vertices[:]=[x,a,-1000,x+10,b,1000,x+10,b,-1000]
        world.triangles[index*2+1].vertices[:]=[x,a,-1000,x,a,1000,x+10,b,1000]
    guest=Guest();process=None;passed=False;checks=[]
    def floor(x):
        base=math.floor(x/10)*10;return height(base)+(height(base+10)-height(base))*(x-base)/10
    def tick():
        if process.poll() is not None:raise RuntimeError('Test SADX exited')
        host.frame+=1;world.revision=host.frame
        for fn,packet in [(dll.ta_transport_write_host,host),(dll.ta_transport_write_world,world)]:
            deadline=time.monotonic()+.2
            while not fn(c.byref(packet)):
                if time.monotonic()>deadline:raise RuntimeError('Transport busy')
                time.sleep(.002)
        time.sleep(.05);return dll.ta_transport_read_guest(c.byref(guest))
    try:
        process=subprocess.Popen([str(args.sadx/'sonic.exe'),'--level','stationsquare','--act','0','--character','sonic'],cwd=args.sadx)
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            if tick() and guest.flags&8 and guest.epoch==host.epoch and guest.status&1:break
        else:raise RuntimeError('No Sonic task')
        for _ in range(35):tick()
        worst=0;host.stickY=80
        for _ in range(80):
            tick();gap=guest.position[1]-floor(guest.position[0]);worst=max(worst,gap)
            assert guest.flags&8 and -.5<gap<2,('Bumpy hover/penetration',gap,list(guest.position),guest.action,guest.status)
        checks.append({'small_crests_and_dips_max_gap_native':worst,'moving_distance':guest.position[0]})
        host.stickY=0
        for _ in range(20):tick()
        host.buttons=0x8000;peak=0
        for _ in range(5):tick();peak=max(peak,guest.position[1]-floor(guest.position[0]))
        assert peak>10,('Ground adhesion pinned jump',peak)
        checks.append({'jump_not_pinned_peak_native':peak})
        host.buttons=0
        for _ in range(60):tick()
        assert guest.status&1 and abs(guest.position[1]-floor(guest.position[0]))<.5
        checks.append({'jump_lands_on_bumpy_floor':True})
        # Replace the nearby geometry with a real lower platform (20 native down).
        # This exceeds the stair skin and must not be treated as ground adhesion.
        world.count=2
        world.triangles[0].vertices[:]=[-3000,-20,-3000,3000,-20,3000,3000,-20,-3000]
        world.triangles[1].vertices[:]=[-3000,-20,-3000,-3000,-20,3000,3000,-20,3000]
        before=guest.position[1];tick()
        assert guest.position[1]>-15 and not guest.status&1,('Real drop snapped instead of falling',list(guest.position))
        for _ in range(60):tick()
        assert guest.status&1 and abs(guest.position[1]+20)<.5
        checks.append({'real_drop_falls_and_lands':True})
        passed=True;print('PASS bumpy ground, free jump and real drops:',checks,flush=True)
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/sonic-bumps-0.1.21.json').write_text(json.dumps({'version':'0.1.21','status':'passed' if passed else 'failed',
            'tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),
            'checks':checks,'actual_zelda_terrain_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
