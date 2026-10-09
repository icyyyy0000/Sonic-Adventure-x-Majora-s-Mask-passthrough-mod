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
    def tick(advance=1):
        if process.poll() is not None:raise RuntimeError(f'SADX exited {process.returncode}')
        host.frame+=advance;world.revision=host.frame
        for function,packet in [(dll.ta_transport_write_host,host),(dll.ta_transport_write_world,world)]:
            deadline=time.monotonic()+.2
            while not function(c.byref(packet)):
                if time.monotonic()>deadline:raise RuntimeError('Transport publication stayed busy')
                time.sleep(.002)
        time.sleep(.05)
        # Compare positions from the requested host frame. One busy mutex or a
        # delayed game frame must not make the catch-up check compare old poses.
        deadline=time.monotonic()+.15
        while time.monotonic()<deadline:
            if dll.ta_transport_read_guest(c.byref(guest)) and guest.hostFrame==host.frame and guest.epoch==host.epoch:return True
            time.sleep(.002)
        return False
    try:
        process=subprocess.Popen([str(args.sadx/'sonic.exe'),'--level','stationsquare','--act','0','--character','sonic'],cwd=args.sadx)
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if tick() and guest.flags&8 and guest.status&1 and guest.epoch==host.epoch:break
        else:raise RuntimeError('Sonic native task did not ground')
        def show(label):
            print(label,'action',guest.action,'anim',guest.animation,'render',guest.renderAnimation,'export',guest.actionIndex,'frame',guest.animationFrame,'flags',guest.renderFlags,'speed',list(guest.nativeSpeed),'hits',guest.hitSequence,guest.hitTargetId,'pos',list(guest.position),flush=True)
        def reset():
            host.buttons=host.stickX=host.stickY=0;host.flags=3;host.targetId=0
            host.epoch+=1;world.epoch=host.epoch;host.position[:]=[0,50,0]
            for _ in range(60):tick()
            assert guest.status&1
        reset();host.stickY=80
        speeds=[]
        for _ in range(35):tick();speeds.append(guest.nativeSpeed[0])
        assert speeds[-1]>speeds[10]>speeds[0],speeds
        show('run');host.stickY=0;coast=[]
        for _ in range(8):tick();coast.append(guest.nativeSpeed[0])
        assert 0<coast[-1]<coast[0]<speeds[-1],coast
        results.append({'acceleration':speeds,'coasting':coast})
        reset();host.buttons=0x8000;clips=set();frames=set()
        for _ in range(5):tick();show('jump');clips.add(guest.actionIndex);frames.add(round(guest.animationFrame,2))
        assert len(frames)>1 and 0xffff not in clips
        results.append({'jump_clips':sorted(clips),'jump_frames':sorted(frames)})
        reset();host.buttons=0x4000;curl=False
        for _ in range(12):tick();show('charge');curl=curl or bool(guest.renderFlags&1)
        assert guest.action==4 and curl
        host.buttons=0;tick();show('dash');assert guest.nativeSpeed[0]>8
        results.append({'charge_ground_curl':curl,'dash_speed':guest.nativeSpeed[0]})
        reset();host.buttons=0x8000
        for _ in range(4):tick()
        host.buttons=0;tick()
        # Native yaw 0 faces +X. The target is airborne to exercise the original
        # steering algorithm and avoid confusing the bounce with landing.
        host.flags=7;host.targetId=100
        host.targetPosition[:]=[guest.position[0]+45,guest.position[1]-8,guest.position[2]+10];host.targetRadius=10
        baseline=guest.hitSequence;host.buttons=0x8000;homing=False
        for _ in range(20):
            tick();show('home1');homing=homing or guest.action==14
            if guest.hitSequence!=baseline:break
        assert guest.hitSequence==baseline+1 and guest.hitTargetId==100,('No homing contact',guest.action,guest.hitSequence)
        assert guest.action==8 and guest.nativeSpeed[1]>0,('No bounce',guest.action,list(guest.nativeSpeed))
        host.buttons=0;host.targetId=101
        host.targetPosition[:]=[guest.position[0]+40,guest.position[1]-3,guest.position[2]-10]
        tick();host.buttons=0x8000
        for _ in range(20):
            tick();show('home2')
            if guest.hitSequence==baseline+2:break
        assert guest.hitSequence==baseline+2 and guest.hitTargetId==101,('No chain',guest.action,guest.hitSequence)
        results.append({'two_target_chain':True,'first_target':100,'second_target':101,'bounce_y_speed':guest.nativeSpeed[1]})
        host.flags=3;host.targetId=0;host.buttons=0;tick();host.buttons=0x8000
        for _ in range(3):tick()
        assert guest.hitSequence==baseline+2,'Removed target generated a hit'
        results.append({'removed_target_safe':True,'native_original_physics':True})
        reset();host.stickY=80
        for _ in range(30):tick()
        start=guest.position[0];tick();one=guest.position[0]-start
        start=guest.position[0];tick(2);two=guest.position[0]-start
        assert two>one*1.8,('Skipped host frame lost native momentum',one,two)
        assert abs(guest.velocity[0]-two/2)<.05
        results.append({'missed_frame_catchup':True,'one_frame_distance':one,'two_frame_distance':two})

        # Withhold world publication long enough to expire its heartbeat, while
        # continuing host updates. Native collision must freeze without resetting
        # the character or releasing it back into Station Square.
        host.stickY=80
        held=list(guest.position);last_speed=list(guest.nativeSpeed)
        for _ in range(30):
            host.frame+=1;dll.ta_transport_write_host(c.byref(host));time.sleep(.05)
            dll.ta_transport_read_guest(c.byref(guest))
        held=list(guest.position)
        for _ in range(5):
            host.frame+=1;dll.ta_transport_write_host(c.byref(host));time.sleep(.05)
            dll.ta_transport_read_guest(c.byref(guest))
        assert not guest.flags&8 and sum((guest.position[i]-held[i])**2 for i in range(3))<.001,('World dropout drift',held,list(guest.position),guest.flags)
        heldSpeed=guest.nativeSpeed[0]
        tick();assert guest.flags&8 and guest.epoch==host.epoch
        assert guest.nativeSpeed[0]>=heldSpeed*.95,('Recovery reset momentum',heldSpeed,list(guest.nativeSpeed))
        assert abs(guest.position[1])<.1,('World recovery lost floor',list(guest.position))
        results.append({'expired_world_freezes_and_recovers':True})
        # Complete absence of host updates must not relocate the Sonic task.
        held=list(guest.position);time.sleep(.3)
        host.frame+=7;tick()
        assert sum((guest.position[i]-held[i])**2 for i in range(3))<16**2,('Heartbeat recovery teleport',held,list(guest.position))
        results.append({'heartbeat_interruption_no_stage_teleport':True})
        # Truncated collision is explicitly unsafe and must hold rather than fall.
        world.flags=1;tick();held=list(guest.position)
        for _ in range(5):tick()
        assert not guest.flags&8 and sum((guest.position[i]-held[i])**2 for i in range(3))<.001
        world.flags=0;tick();assert guest.flags&8
        results.append({'truncated_world_safe_hold_and_recovery':True})
        passed=True
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/sonic-native-0.1.21.json').write_text(json.dumps({'version':'0.1.21','tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),'status':'passed' if passed else 'failed','method':'Installed original SADX tasks with streamed collision/contact adapters and synthetic host packets','checks':results,'zelda_gameplay_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
