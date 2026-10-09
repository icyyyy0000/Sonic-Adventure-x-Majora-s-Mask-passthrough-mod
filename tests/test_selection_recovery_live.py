"""Rapid native task swaps and all-character heartbeat gaps; own test process only."""
import argparse,ctypes as c,hashlib,json,subprocess,time
from pathlib import Path
from test_transport import Host,Guest
from test_world import World
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sadx',type=Path,required=True);args=ap.parse_args()
    processes=subprocess.check_output(['tasklist','/fo','csv'],text=True).lower()
    assert '"sonic.exe"' not in processes and '"zelda64recompiled.exe"' not in processes,'Close user games before this isolated test.'
    dll=c.CDLL(str(ROOT/'build/native/termina_bridge.dll'))
    dll.ta_transport_write_host.argtypes=[c.POINTER(Host)];dll.ta_transport_write_world.argtypes=[c.POINTER(World)]
    dll.ta_transport_read_guest.argtypes=[c.POINTER(Guest)]
    host=Host(scene=17,epoch=870,character=1,flags=3);host.position[:]=[0,50,0]
    world=World(scene=17,epoch=870,count=2,radius=3000)
    for t in world.triangles[:2]:t.flags=1
    world.triangles[0].vertices[:]=[-3000,0,-3000,3000,0,3000,3000,0,-3000]
    world.triangles[1].vertices[:]=[-3000,0,-3000,-3000,0,3000,3000,0,3000]
    guest=Guest();process=None;checks=[];passed=False
    def tick():
        assert process.poll() is None,'Test SADX exited'
        host.frame+=1;world.revision=host.frame
        for fn,packet in [(dll.ta_transport_write_host,host),(dll.ta_transport_write_world,world)]:
            end=time.monotonic()+.2
            while not fn(c.byref(packet)):
                assert time.monotonic()<end,'Transport stayed busy';time.sleep(.002)
        time.sleep(.05)
        deadline=time.monotonic()+.02
        while not dll.ta_transport_read_guest(c.byref(guest)):
            if time.monotonic()>deadline:return False
            time.sleep(.001)
        return True
    try:
        process=subprocess.Popen([str(args.sadx/'sonic.exe'),'--level','stationsquare','--act','0','--character','sonic'],cwd=args.sadx)
        end=time.monotonic()+35
        while time.monotonic()<end:
            if tick() and guest.flags&8 and guest.epoch==host.epoch:break
        else:raise AssertionError('Initial task never activated')
        # Switching faster than the old one-second cooldown must not accumulate
        # pending selections. No OS input is sent to the user's controller.
        worst=0
        for character in [6,2,1,4,3,5,1,6,1,2,3,4,5,6,1]:
            host.character=character;host.stickX=host.stickY=0;host.buttons=0
            start=time.monotonic()
            for _ in range(12):
                tick()
                if guest.character==character and guest.flags&8 and guest.epoch==host.epoch:break
            else:raise AssertionError(('Selection did not recover promptly',character,guest.character,guest.flags))
            worst=max(worst,time.monotonic()-start)
        checks.append({'rapid_selection_roster':[1,2,3,4,5,6],'maximum_sync_seconds':round(worst,3)})
        # Reproduce the original trigger: inherited Hurt before Knuckles -> Tails.
        host.character=3;host.buttons=host.stickY=0
        for _ in range(20):
            tick()
            if guest.character==3 and guest.flags&8:break
        assert guest.character==3 and guest.flags&8
        k=c.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[c.c_uint,c.c_int,c.c_uint];k.OpenProcess.restype=c.c_void_p
        k.ReadProcessMemory.argtypes=[c.c_void_p,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)]
        k.WriteProcessMemory.argtypes=[c.c_void_p,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)]
        k.CloseHandle.argtypes=[c.c_void_p];k.GetProcessId.argtypes=[c.c_void_p];k.GetProcessId.restype=c.c_uint
        handle=k.OpenProcess(0x38,False,process.pid);assert handle and k.GetProcessId(handle)==process.pid
        try:
            address=c.c_uint32();n=c.c_size_t();assert k.ReadProcessMemory(handle,0x3B42E10,c.byref(address),4,c.byref(n))
            hurt=c.c_uint16(guest.status|4);assert address.value and k.WriteProcessMemory(handle,address.value+4,c.byref(hurt),2,c.byref(n))
            host.character=2
            for _ in range(20):
                tick()
                if guest.character==2 and guest.flags&8:break
            assert guest.character==2 and guest.flags&8,'Forced Hurt switch failed to initialize Tails'
        finally:k.CloseHandle(handle)
        checks.append({'knuckles_to_tails_inherited_hurt_flag_switch':True})
        for character in range(1,7):
            host.character=character;host.position[:]=[0,50,0];host.epoch+=1;world.epoch=host.epoch
            for _ in range(60):tick()
            host.stickY=60
            for _ in range(10):tick()
            pos=list(guest.position);speed=guest.nativeSpeed[0]
            time.sleep(.4);host.frame+=8;tick()
            assert guest.character==character and guest.flags&8
            distance=sum((guest.position[i]-pos[i])**2 for i in range(3))**.5
            assert distance<25,('Gap caused stage teleport/catchup burst',character,pos,list(guest.position),distance)
            assert guest.nativeSpeed[0]>=speed*.8,('Gap discarded momentum',character,speed,list(guest.nativeSpeed))
            world.flags=1;tick();held=list(guest.position);heldSpeed=guest.nativeSpeed[0]
            for _ in range(4):
                tick();assert not guest.flags&8 and list(guest.position)==held,('Incomplete geometry did not hold',character)
            world.flags=0
            # Guest publication and native stepping run asynchronously at 60 Hz;
            # the first host poll can still describe the held simulation frame.
            for recoveryTicks in range(1,4):
                tick()
                if guest.flags&8:break
            assert guest.flags&8 and guest.nativeSpeed[0]>=heldSpeed*.8,('Geometry recovery discarded momentum',character,guest.flags,heldSpeed,list(guest.nativeSpeed))
            host.stickY=0
            checks.append({'character':character,'heartbeat_recovery_distance':round(distance,3),'momentum_preserved':True,'incomplete_geometry_hold_and_recovery':True,'geometry_recovery_host_ticks':recoveryTicks})
        passed=True;print('PASS rapid character selection and six-character heartbeat recovery',checks,flush=True)
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:process.terminate();process.wait(timeout=5)
        (ROOT/'docs/selection-recovery-0.1.21.json').write_text(json.dumps({'version':'0.1.21','status':'passed' if passed else 'failed',
            'tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),
            'checks':checks,'physical_controller_gameplay_retest_needed':True},indent=2)+'\n')
if __name__=='__main__':main()
