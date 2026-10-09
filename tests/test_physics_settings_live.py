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
        speedDistances=[]
        for percent in (100,300):
            flat();host.flags=3|((percent//25)<<24);reset(1);host.stickY=80;start=guest.position[0];tick(20);speedDistances.append(guest.position[0]-start)
        assert speedDistances[1]>speedDistances[0]*2.5,('Character speed ignored',speedDistances)
        checks.append({'character_speed_100_vs_300_distances':speedDistances})
        gravityPeaks=[]
        for percent in (50,200):
            flat();host.flags=3|((percent//25)<<16);reset(1);host.buttons=0x8000;peak=0
            for i in range(70):
                if i==3:host.buttons=0
                tick();peak=max(peak,guest.position[1])
            gravityPeaks.append(peak)
        assert gravityPeaks[0]>gravityPeaks[1]*1.25,('Gravity slider has no effect',gravityPeaks)
        checks.append({'gravity_50_vs_200_jump_peaks':gravityPeaks})
        amyPeaks=[]
        for percent in (50,200):
            flat();host.flags=3|((percent//25)<<20);reset(4);host.stickY=80;tick(60);print("Amy run",percent,guest.action,list(guest.nativeSpeed),list(guest.position),flush=True);host.buttons=0x4000;peak=0
            for i in range(45):
                if i==5:host.buttons=0
                tick();peak=max(peak,guest.position[1]);
                if i<8:print("Amy vault",percent,i,guest.action,guest.status,list(guest.nativeSpeed),guest.position[1],flush=True)
            amyPeaks.append(peak)
        assert amyPeaks[1]>amyPeaks[0]*1.5,('Amy height slider has no effect',amyPeaks)
        checks.append({'amy_hammer_height_50_vs_200_peaks':amyPeaks})
        gammaDistances=[]
        for percent in (100,500):
            flat();host.flags=3|64;host.targetRadius=percent;reset(6);host.buttons=0x8000;tick(20);start=guest.position[0];host.stickY=80;tick(10);gammaDistances.append(guest.position[0]-start)
        assert gammaDistances[1]>gammaDistances[0]*3,('Gamma 500 percent is not applied',gammaDistances)
        checks.append({'gamma_hover_100_vs_500_distances':gammaDistances})
        passed=True;print('PASS slider physics checks',checks,flush=True)
    finally:
        dll.ta_transport_close()
        if handle:k.CloseHandle(handle)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/physics-settings-live-0.1.21.json').write_text(json.dumps({'version':'0.1.21','status':'passed' if passed else 'failed','tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),'checks':checks,'actual_zelda_visuals_and_terrain_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
