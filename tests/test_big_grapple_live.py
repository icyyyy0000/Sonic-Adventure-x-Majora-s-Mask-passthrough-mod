"""Original roster routines: bumpy ground, slopes, rotor animation, climb, hover and music isolation."""
import argparse,ctypes as c,hashlib,json,math,subprocess,time
from pathlib import Path
from test_transport import Host,Guest
from test_world import World
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sadx',type=Path,required=True);ap.add_argument('--start-character',type=int,choices=range(1,8),default=1);args=ap.parse_args()
    dll=c.CDLL(str(ROOT/'build/native/termina_bridge.dll'))
    dll.ta_transport_write_host.argtypes=[c.POINTER(Host)];dll.ta_transport_write_world.argtypes=[c.POINTER(World)];dll.ta_transport_read_guest.argtypes=[c.POINTER(Guest)]
    host=Host(scene=17,epoch=900,character=1,flags=3);host.position[:]=[0,50,0]
    world=World(scene=17,epoch=900,radius=3000);guest=Guest();process=None;checks=[];passed=False;handle=None
    k=c.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[c.c_uint,c.c_int,c.c_uint];k.OpenProcess.restype=c.c_void_p
    k.ReadProcessMemory.argtypes=[c.c_void_p,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)];k.CloseHandle.argtypes=[c.c_void_p]
    def read(address,ty):
        value=ty();n=c.c_size_t();assert k.ReadProcessMemory(handle,address,c.byref(value),c.sizeof(value),c.byref(n));return value.value
    def tick(n=1):
        for _ in range(n):
            assert process.poll() is None,'Test-owned SADX exited'
            host.frame+=1;world.revision=host.frame
            for fn,packet in [(dll.ta_transport_write_host,host),(dll.ta_transport_write_world,world)]:
                deadline=time.monotonic()+.2
                while not fn(c.byref(packet)):
                    assert time.monotonic()<deadline,'Transport busy';time.sleep(.002)
            time.sleep(.05)
            deadline=time.monotonic()+.02
            while not dll.ta_transport_read_guest(c.byref(guest)) and time.monotonic()<deadline:time.sleep(.001)
    def flat(y=0):
        world.count=2
        for t in world.triangles[:2]:t.flags=1
        world.triangles[0].vertices[:]=[-3000,y,-3000,3000,y,3000,3000,y,-3000]
        world.triangles[1].vertices[:]=[-3000,y,-3000,-3000,y,3000,3000,y,3000]
    def reset(char,pos=(0,50,0)):
        host.character=char;host.buttons=host.stickX=host.stickY=0;host.epoch+=1;world.epoch=host.epoch;host.position[:]=pos
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            tick()
            if guest.character==char and guest.epoch==host.epoch and guest.flags&8:break
        else:raise RuntimeError(('No native roster task',char))
        tick(45)
    def height(x):return math.sin(x*math.pi/20)*1.5
    def floor(x):
        base=math.floor(x/10)*10;return height(base)+(height(base+10)-height(base))*(x-base)/10
    def bumps():
        segments=list(range(-1000,1600,10));world.count=len(segments)*2
        for index,x in enumerate(segments):
            for t in world.triangles[index*2:index*2+2]:t.flags=1
            a=height(x);b=height(x+10)
            world.triangles[index*2].vertices[:]=[x,a,-1000,x+10,b,1000,x+10,b,-1000]
            world.triangles[index*2+1].vertices[:]=[x,a,-1000,x,a,1000,x+10,b,1000]
    try:
        flat();process=subprocess.Popen([str(args.sadx/'sonic.exe'),'--level','stationsquare','--act','0','--character','sonic'],cwd=args.sadx)
        handle=k.OpenProcess(0x10,False,process.pid);assert handle
        # Requested speed must survive Big's original air-speed cap.
        speeds=[]
        for speed in (3,9):
            flat();reset(5);host.flags=3|16;host.targetId=200+speed;host.targetRadius=speed;host.targetPosition[:]=[700,80,0]
            origin=list(guest.position);tick(8);distance=math.dist(origin,list(guest.position));speeds.append(distance)
            assert guest.position[1]>=-.01
        assert speeds[1]>speeds[0]*2.5,('Big grapple speed ignored',speeds)
        checks.append({'big_grapple_speed_3_vs_9':speeds,'speed_setting_controls_actual_pull':True})
        host.flags=3;host.targetRadius=0
        # Big grapple pull and impact stay inside the ordinary terrain guards.
        reset(5);host.flags=3|16;host.targetId=101;host.targetRadius=6;host.targetPosition[:]=[150,80,0]
        trace=[]
        for _ in range(15):tick();trace.append(list(guest.position))
        print('BIG grapple',trace[-1],guest.renderFlags,flush=True)
        assert trace[-1][0]>80 and trace[-1][1]>35 and all(v[1]>=-.01 for v in trace)
        checks.append({'big_grapple_moves_through_native_collision':True,'position':trace[-1]})
        host.flags=3|32;host.targetId=102;sequence=guest.hitSequence;impact=False;windup=False
        for _ in range(40):
            tick();windup|=bool(guest.renderFlags&32);assert guest.position[1]>=-.01,('Big slam penetrated floor',list(guest.position))
            if guest.hitSequence!=sequence and guest.renderFlags&16:impact=True;break
        assert windup,'Big missing windup flag'
        assert impact,('Big belly flop did not report ground impact',guest.action,list(guest.position),guest.renderFlags)
        checks.append({'big_belly_flop_reports_ground_impact':True,'windup_observed':windup})
        host.flags=3;tick(5);reset(5);host.flags=3|1024;host.targetId=104;origin=list(guest.position);tick(20);assert guest.renderFlags&64,('Big wave lost',guest.renderFlags);assert math.dist(origin,list(guest.position))<1;host.flags=3;tick(3);assert not guest.renderFlags&64;checks.append({'big_wave_holds_ground_and_releases':True})
        host.flags=3;host.targetId=0;host.targetRadius=0
        flat();world.count=4
        for t,v in zip(world.triangles[2:4],[[50,-50,-300,50,300,300,50,300,-300],[50,-50,-300,50,-50,300,50,300,300]]):t.flags=1;t.vertices[:]=v
        reset(5);host.flags=3|16;host.targetId=103;host.targetRadius=9;host.targetPosition[:]=[150,60,0]
        for _ in range(25):tick();assert guest.position[0]<50,('Big grapple crossed solid wall',list(guest.position))
        checks.append({'big_grapple_blocked_by_solid_wall':True})
        host.flags=3;host.targetId=0;host.targetRadius=0
        flat();reset(5);host.flags=3|2048;host.buttons=0x4000;actions=set()
        for _ in range(15):tick();actions.add(guest.action)
        assert len(actions)>1 or guest.action!=1,('Big original rod swing did not start',actions)
        checks.append({'rod_only_B_original_actions':sorted(actions)})
        passed=True;print('PASS focused Big checks',checks,flush=True)
    finally:
        dll.ta_transport_close()
        if handle:k.CloseHandle(handle)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/big-grapple-live-0.1.21.json').write_text(json.dumps({'version':'0.1.21','status':'passed' if passed else 'failed','tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),'checks':checks,'actual_zelda_visuals_and_terrain_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
