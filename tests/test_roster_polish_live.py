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
    if args.start_character>1:
        previous=json.loads((ROOT/'docs/roster-polish-0.1.21.json').read_text())
        if previous['tested_dll_sha256']==hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest():
            checks=[item for item in previous['checks'] if item.get('character',7)<args.start_character]
        else:assert args.start_character==7,'Earlier terrain checks must match the installed build'
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
        for char in range(args.start_character,7):
            bumps();reset(char);host.stickY=80;worst=0
            for _ in range(45):
                tick();gap=guest.position[1]-floor(guest.position[0]);worst=max(worst,gap)
                assert guest.flags&8 and -.5<gap<2,('Bumpy terrain',char,gap,list(guest.position),guest.action)
            host.stickY=0;tick(20);host.buttons=0x8000;peak=0
            for _ in range(4):tick();peak=max(peak,guest.position[1]-floor(guest.position[0]))
            assert peak>10,('Ground adhesion pinned jump',char,peak)
            host.buttons=0;tick(100)
            assert guest.status&1 and abs(guest.position[1]-floor(guest.position[0]))<.5,('Landing',char,list(guest.position))
            # Gamma's larger native collision body can step down twenty units.
            # Use a drop beyond his step/contact reach to test free falling.
            drop=80 if char==6 else 20
            flat(-drop);tick();assert guest.position[1]>-drop+5 and not guest.status&1,('Real drop snapped',char,list(guest.position))
            tick(60);assert guest.status&1 and abs(guest.position[1]+drop)<.5
            for grade in (.8,1.5,2.5):
                flat()
                for t in world.triangles[:2]:
                    for i in range(3):t.vertices[i*3+1]=t.vertices[i*3]*grade
                reset(char);host.stickY=80
                for _ in range(25):
                    tick();assert guest.position[0]*grade-guest.position[1]<.5,('Slope penetration',char,grade,list(guest.position))
                host.stickY=-80
                for _ in range(25):
                    tick();assert guest.position[0]*grade-guest.position[1]<.5,('Downhill penetration',char,grade,list(guest.position))
            checks.append({'character':char,'bumpy_ground_max_gap':worst,'jump_peak':peak,'free_drop_and_landing':True,'slopes_degrees':[38.7,56.3,68.2]});print('PASS roster terrain',checks[-1],flush=True)
        flat();reset(2);host.buttons=0x8000;phases=set();flew=False
        for _ in range(40):
            tick()
            if guest.action==15:
                flew=True;assert guest.renderFlags&2,('Missing rotor flags',guest.actionIndex,guest.renderFlags);phases.add(guest.renderFlags>>16)
        assert flew and len(phases)>1,('Rotor not advancing',phases)
        checks.append({'tails_original_rotor_advances':True,'distinct_phases':len(phases)});print('PASS Tails rotor',checks[-1],flush=True)
        # Compare the original hover FSM to releasing A on an identical jump.
        flat();hover=[]
        for held in (False,True):
            reset(6);host.buttons=0x8000;trace=[]
            for i in range(30):
                if not held and i==3:host.buttons=0
                tick();trace.append({'y':guest.position[1],'action':guest.action,'speedY':guest.nativeSpeed[1]})
            hover.append(trace)
        assert hover[1][20]['y']>hover[0][20]['y']+5,('Gamma original hover not sustained',hover)
        assert all(abs(item['speedY']+.4)<.01 for item in hover[1][-5:]),('Hover descent not capped by native booster',hover[1])
        checks.append({'gamma_hold_A_hover_height':hover[1][20]['y'],'gamma_release_A_height':hover[0][20]['y']});print('PASS Gamma hover',checks[-1],flush=True)
        # Universal climb adapter uses the original climb motion on either
        # wall winding and inclined surfaces without the original material gate.
        for tilt,reverse in [(0,False),(0,True),(.1,True)]:
            flat();world.count=4;world.center[:]=[0,0,0]
            vertices=[[60,-50,-300,60+tilt*300,300,300,60+tilt*300,300,-300],[60,-50,-300,60,-50,300,60+tilt*300,300,300]]
            for t,v in zip(world.triangles[2:4],vertices):
                t.flags=1
                if reverse:v=v[:3]+v[6:9]+v[3:6]
                t.vertices[:]=v
            reset(3);host.stickY=80;host.buttons=0x8000;tick(3);host.buttons=0;tick(2);host.buttons=0x8000
            climbed=False;startY=0;lastY=0;trace=[]
            for _ in range(80):
                tick();trace.append((guest.action,list(guest.position)))
                if guest.action==0x18:
                    if not climbed:startY=guest.position[1]
                    climbed=True;lastY=guest.position[1]
            print('KNUCKLES climb',tilt,reverse,climbed,startY,lastY,flush=True)
            assert climbed and lastY>startY+5,('Native wall climb',tilt,reverse,climbed,startY,lastY)
            checks.append({'knuckles_native_climb':True,'wall_tilt':tilt,'reversed_winding':reverse,'height_gain':lastY-startY})
        # Ceiling latch uses the same arbitrary-surface query and original climb motion.
        flat();world.count=4
        for t,v in zip(world.triangles[2:4],[[ -300,18,-300,300,18,-300,300,18,300],[-300,18,-300,300,18,300,-300,18,300]]):t.flags=1;t.vertices[:]=v
        reset(3,(0,0,0));host.buttons=0x8000;ceiling=False
        for _ in range(20):
            tick()
            if guest.action==24 and guest.rotationX==32768:ceiling=True
        print('KNUCKLES ceiling',ceiling,list(guest.position),guest.rotationX,flush=True)
        assert ceiling,'Knuckles failed to attach to a solid ceiling'
        start=list(guest.position);host.stickY=80;tick(10)
        assert math.hypot(guest.position[0]-start[0],guest.position[2]-start[2])>5
        assert guest.position[1]<18,'Knuckles crossed the ceiling'
        host.buttons=0;tick(5);assert guest.action!=24,'Knuckles failed to release ceiling'
        checks.append({'knuckles_ceiling_climb_and_release':True})
        # Upgrade-dependent original spin attacks are granted only to the owned task.
        flat()
        for char in (2,4):
            reset(char);host.buttons=0x4000;actions=[]
            for _ in range(35):tick();actions.append(guest.action)
            print('SPIN',char,sorted(set(actions)),flush=True)
            assert 20 in actions,('Original spin attack missing',char,actions)
            checks.append({'original_spin_attack_character':char,'action_20_observed':True})
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
        # Gamma's setting scales horizontal hover displacement, retaining original vertical FSM.
        distances=[]
        for percent in (50,150):
            flat();reset(6);host.flags=3|64;host.targetRadius=percent;host.buttons=0x8000;tick(20)
            start=guest.position[0];host.stickY=80;tick(15);distances.append(guest.position[0]-start)
            print('GAMMA speed',percent,distances[-1],guest.action,guest.nativeSpeed[1],flush=True)
        assert distances[1]>distances[0]*1.5,('Gamma hover slider has no effect',distances)
        checks.append({'gamma_hover_speed_slider':True,'50_percent_distance':distances[0],'150_percent_distance':distances[1]})
        host.flags=3;host.targetRadius=0
        # A sustained charge should start one stream, not restart every host packet.
        reset(1);before=(args.sadx/'mods/TerminaAdventureBridge/bridge.log').read_text().count('Spindash charge stream started')
        host.buttons=0x4000;tick(50)
        after=(args.sadx/'mods/TerminaAdventureBridge/bridge.log').read_text().count('Spindash charge stream started')
        print('CHARGE starts',after-before,flush=True)
        assert after-before==1,('Spindash refresh loop restarts',after-before)
        checks.append({'sustained_spindash_charge_starts':after-before})
        # Yield to Link: owned character streams stop and staging controls are isolated.
        host.character=0;host.flags=0;host.buttons=0;tick(15)
        class Sound(c.Structure):
            _fields_=[('priority',c.c_int32),('timer',c.c_int32),('id',c.c_int32),('mode',c.c_uint32),('tone',c.c_int32),('rest',c.c_byte*36)]
        sounds=(Sound*36)();n=c.c_size_t();assert k.ReadProcessMemory(handle,0x3B292F8,c.byref(sounds),c.sizeof(sounds),c.byref(n))
        assert not any(v.mode and v.tone==0x2ff for v in sounds),'Sonic charge leaked into Link'
        checks.append({'owned_charge_sound_stopped_when_link_selected':True})
        assert read(0x3ABDFA0,c.c_int)==0,'SADX stage music is still playing'
        checks.append({'stage_music_stopped_separately_from_character_effects':True})
        passed=True
    finally:
        dll.ta_transport_close()
        if handle:k.CloseHandle(handle)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/roster-polish-0.1.21.json').write_text(json.dumps({'version':'0.1.21','status':'passed' if passed else 'failed','tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),'checks':checks,'actual_zelda_visuals_and_terrain_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
