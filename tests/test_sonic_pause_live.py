"""Pause/resume regressions against the installed original Sonic task.

Synthetic host packets exercise both stopped heartbeats and explicit menu states.
Only the SADX process started by this test is stopped. No physical input injection.
"""
import argparse,ctypes as c,hashlib,json,subprocess,time
from pathlib import Path
from test_transport import Host,Guest
from test_world import World
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sadx',type=Path,required=True);args=ap.parse_args()
    dll=c.CDLL(str(ROOT/'build/native/termina_bridge.dll'))
    dll.ta_transport_write_host.argtypes=[c.POINTER(Host)]
    dll.ta_transport_write_world.argtypes=[c.POINTER(World)]
    dll.ta_transport_read_guest.argtypes=[c.POINTER(Guest)]
    host=Host(scene=17,epoch=400,character=1,flags=3)
    host.position[:]=[0,50,0]
    world=World(scene=17,epoch=400,count=2,radius=3000)
    for t in world.triangles[:2]:t.flags=1
    world.triangles[0].vertices[:]=[-3000,0,-3000,3000,0,3000,3000,0,-3000]
    world.triangles[1].vertices[:]=[-3000,0,-3000,-3000,0,3000,3000,0,3000]
    guest=Guest();process=None;checks=[];passed=False
    def tick(publish_world=True,advance=1):
        if process.poll() is not None:raise RuntimeError('Test SADX process exited')
        host.frame+=advance;world.revision=host.frame
        packets=[(dll.ta_transport_write_host,host)]
        if publish_world:packets.append((dll.ta_transport_write_world,world))
        for fn,packet in packets:
            deadline=time.monotonic()+.2
            while not fn(c.byref(packet)):
                if time.monotonic()>deadline:raise RuntimeError('Transport busy')
                time.sleep(.002)
        time.sleep(.05)
        # Production transport intentionally declines a read if its mutex is
        # busy. Retry briefly, as the host's existing snapshot cache does; a
        # single contended read is not a failed pause/restart recovery.
        deadline=time.monotonic()+.02
        while not dll.ta_transport_read_guest(c.byref(guest)):
            assert time.monotonic()<deadline,'No guest snapshot after bounded read retry'
            time.sleep(.001)
    def reset():
        host.epoch+=1;world.epoch=host.epoch
        host.scene=world.scene=17;host.character=1;host.flags=3
        host.buttons=host.stickX=host.stickY=host.targetId=0
        host.position[:]=[0,50,0]
        for _ in range(45):tick()
        assert guest.flags&8 and guest.status&1
    def snapshot():return (list(guest.position),list(guest.nativeSpeed),guest.action,guest.hitSequence)
    def explicit_pause(buttons=None):
        before=snapshot();host.flags=(host.flags&~1)|8
        if buttons is not None:host.buttons=buttons
        for _ in range(22):tick(False)
        after=snapshot()
        assert not guest.flags&8
        assert sum((after[0][i]-before[0][i])**2 for i in range(3))<.001,('Pause drift',before,after)
        assert after[1:]==before[1:],('Pause changed FSM/speed/hits',before,after)
        host.flags=(host.flags|1)&~8
        return before
    try:
        process=subprocess.Popen([str(args.sadx/'sonic.exe'),'--level','stationsquare','--act','0','--character','sonic'],cwd=args.sadx)
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            host.frame+=1;world.revision=host.frame
            dll.ta_transport_write_host(c.byref(host));dll.ta_transport_write_world(c.byref(world))
            time.sleep(.05)
            if dll.ta_transport_read_guest(c.byref(guest)) and guest.flags&8 and guest.epoch==host.epoch and guest.status&1:break
        else:raise RuntimeError('Sonic never grounded')
        reset();host.stickY=80
        for _ in range(25):tick()
        for _ in range(3):
            before=explicit_pause();tick(advance=8)
            displacement=guest.position[0]-before[0][0]
            assert guest.flags&8 and guest.nativeSpeed[0]>=before[1][0]*.95
            assert 0<displacement<before[1][0]*4+1,('Resume catchup burst',before,snapshot())
            assert abs(guest.position[1])<.1
        checks.append('Repeated explicit pauses preserve running momentum/floor and resume with one host tick')
        reset();host.buttons=0x8000
        for _ in range(3):tick()
        assert not guest.status&1 and guest.position[1]>10
        before=explicit_pause();tick()
        assert guest.flags&8 and not guest.status&1 and guest.position[1]>10
        assert guest.action==before[2] and abs(guest.position[1]-before[0][1])<20
        checks.append('Airborne pause preserves jump FSM without ground reset or teleport')
        reset();host.buttons=0x4000
        for _ in range(10):tick()
        assert guest.action==4
        explicit_pause();tick();assert guest.action==4
        host.buttons=0;tick();assert guest.nativeSpeed[0]>8
        checks.append('Paused spindash charge survives and launches on release')
        reset();explicit_pause(0x8000);tick()
        assert guest.status&1,('Menu A became a jump',snapshot())
        host.buttons=0;tick();host.buttons=0x8000;tick()
        assert not guest.status&1
        checks.append('Held menu A creates no phantom ability; fresh release/press jumps normally')
        reset();host.stickY=80
        for _ in range(20):tick()
        time.sleep(.4);before=snapshot()
        # The guest may publish nothing while the stopped host heartbeat is old.
        # Resume must retain momentum and ignore elapsed pause time.
        tick(advance=50)
        assert guest.nativeSpeed[0]>=before[1][0]*.95
        assert 0<guest.position[0]-before[0][0]<before[1][0]*4+1
        checks.append('Stopped host heartbeat resumes without catchup movement or stage restoration')
        reset();host.buttons=0x8000
        for _ in range(4):tick()
        host.buttons=0;tick();host.flags=7;host.targetId=501;host.targetRadius=10
        host.targetPosition[:]=[guest.position[0]+90,guest.position[1]-8,guest.position[2]+10]
        baseline=guest.hitSequence;host.buttons=0x8000;tick()
        assert guest.action==14 and guest.hitSequence==baseline,('No ongoing homing to pause',snapshot())
        explicit_pause()
        for _ in range(15):
            tick()
            if guest.hitSequence!=baseline:break
        assert guest.hitSequence==baseline+1 and guest.hitTargetId==501 and guest.action==8
        host.buttons=0;host.targetId=502
        host.targetPosition[:]=[guest.position[0]+40,guest.position[1]-3,guest.position[2]-10]
        tick();host.buttons=0x8000
        for _ in range(15):
            tick()
            if guest.hitSequence==baseline+2:break
        assert guest.hitSequence==baseline+2 and guest.hitTargetId==502
        checks.append('Paused homing resumes, hits once, bounces and chains to the next target')
        # A scene/epoch change during suspension still performs a real takeover.
        reset();explicit_pause();host.flags=2;host.epoch+=1;world.epoch=host.epoch
        host.scene=world.scene=18;host.position[:]=[500,50,0]
        for _ in range(4):tick(False)
        host.flags=3
        for _ in range(40):tick()
        assert guest.epoch==host.epoch and guest.scene==18 and abs(guest.position[0]-500)<1 and guest.status&1
        # Reused epoch + rolled-back frame is a defensive restart fallback.
        host.frame=0;host.position[:]=[-500,50,0]
        for _ in range(40):tick()
        assert abs(guest.position[0]+500)<1 and guest.status&1
        checks.append('Frame counter rollback recovers an old same-epoch native session')
        host.flags=10;tick(False);host.character=0;host.flags=0
        for _ in range(4):tick()
        assert not guest.flags&8
        checks.append('New scene/epoch resets correctly; Link relinquishes ownership even during suspension')
        passed=True
        print('PASS:',*checks,sep='\n',flush=True)
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/sonic-pause-0.1.21.json').write_text(json.dumps({'version':'0.1.21','status':'passed' if passed else 'failed',
            'tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),
            'method':'Installed original SADX Sonic task driven by synthetic host menu and heartbeat packets',
            'checks':checks,'actual_zelda_pause_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
