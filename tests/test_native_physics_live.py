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
        for character,name in [(1,'Sonic'),(3,'Knuckles'),(2,'Tails'),(4,'Amy'),(5,'Big'),(6,'Gamma')]:
            host.character=character;host.buttons=0;host.stickX=host.stickY=0
            host.epoch+=1;world.epoch=host.epoch
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                if tick() and guest.character==character and guest.flags&8 and guest.epoch==host.epoch:break
            else:raise RuntimeError(f'{name}: native collision ownership did not activate')
            for _ in range(45):tick()
            grounded=bool(guest.status&1)
            assert grounded and abs(guest.position[1])<20,(name,'foreign floor failed',list(guest.position),guest.status,guest.action)
            idleAction=guest.actionIndex;idleFrame=guest.animationFrame
            start=list(guest.position);host.stickY=80
            for _ in range(20):tick()
            moved=((guest.position[0]-start[0])**2+(guest.position[2]-start[2])**2)**.5
            print(name,'movement',moved,'action',guest.action,'status',guest.status,'frame',guest.hostFrame,host.frame,'motion',guest.actionIndex,guest.animationFrame,'blend',guest.animationBlend,flush=True)
            assert guest.actionIndex!=0xffff,('Missing original animation',name)
            assert guest.actionIndex!=idleAction or guest.animationFrame!=idleFrame,('Native animation did not advance',name)
            assert moved>10,(name,'native movement did not respond',moved)
            host.stickY=0;host.buttons=0x8000;peak=guest.position[1]
            for _ in range(3):tick();peak=max(peak,guest.position[1])
            host.buttons=0
            for _ in range(25):tick();peak=max(peak,guest.position[1])
            print(name,'jump',peak,'action',guest.action,'status',guest.status,flush=True)
            assert peak>10,(name,'native jump did not respond',peak)
            results.append({'character':name,'foreign_floor_grounded':grounded,'landing_y':round(guest.position[1],3),'model_offset_y':round(guest.modelOffsetY,3),'distance':round(moved,3),'jump_peak':round(peak,3),'animation_action':guest.actionIndex})
            print('PASS',results[-1],flush=True)
        # Native task headings under the streamed coordinate basis.
        import math
        host.character=1;host.buttons=0;host.stickY=0
        for yaw in (0,16384,32768,49152):
            host.epoch+=1;world.epoch=host.epoch;host.position[:]=[0,50,0]
            host.cameraYaw=yaw
            for _ in range(55):tick()
            start=list(guest.position);host.stickY=80
            for _ in range(25):tick()
            dx=guest.position[0]-start[0];dz=guest.position[2]-start[2]
            expected=(math.cos(yaw*math.tau/65536),math.sin(yaw*math.tau/65536))
            dot=(dx*expected[0]+dz*expected[1])/max(.001,math.hypot(dx,dz))
            print('HEADING',yaw,dx,dz,'native yaw',guest.yaw,'dot',dot,flush=True)
            assert dot>.95,('Native direction basis',yaw,dx,dz,dot)
            results.append({'camera_native_yaw':yaw,'direction_dot':round(dot,4)})
            host.stickY=0
        host.cameraYaw=0;host.character=2;host.epoch+=1;world.epoch=host.epoch
        host.position[:]=[0,50,0]
        for _ in range(60):tick()
        host.buttons=0x8000;peak=guest.position[1];flew=False
        for _ in range(40):
            tick();peak=max(peak,guest.position[1]);flew=flew or guest.action==15
        print('TAILS hold flight',peak,flew,'action',guest.action,flush=True)
        assert flew and peak>35,('Tails held A flight',peak,flew,guest.action)
        host.buttons=0
        for _ in range(110):tick()
        assert guest.status&1,('Tails release landing',list(guest.position),guest.action)
        results.append({'tails_held_A_native_flight_peak':round(peak,3),'released_A_landed':True})
        host.epoch=world.epoch=222
        # Amy's run + B vault is handled by her original task.
        host.character=4;host.buttons=0;host.stickY=80
        for _ in range(60):tick()
        host.buttons=0x4000;peak=guest.position[1]
        for _ in range(5):tick();peak=max(peak,guest.position[1])
        host.buttons=0
        for _ in range(25):tick();peak=max(peak,guest.position[1])
        assert peak>15,('Amy native hammer vault',peak)
        results.append({'Amy_hammer_vault_peak':round(peak,3)})
        print('PASS Amy original hammer vault',peak,flush=True)
        host.flags=2;host.stickY=0;host.buttons=0
        for _ in range(3):tick()
        before=list(guest.position)
        for _ in range(10):tick()
        assert list(guest.position)==before and not (guest.flags&8),'Native task did not yield to host pause'
        host.position[:]=[-100,50,170];host.flags=3
        for _ in range(3):tick()
        assert abs(guest.position[0]+100)<1 and guest.position[1]>30,'Resume failed to reset to scripted host position'
        host.epoch=world.epoch=223;host.position[:]=[230,50,170]
        for _ in range(3):tick()
        assert guest.epoch==223 and abs(guest.position[0]-230)<1,'Scene epoch reset failed'
        # Uphill collision and visual tilt use the same original native solver.
        host.character=1;host.epoch=world.epoch=224;host.position[:]=[100,100,0]
        for triangle in world.triangles[:2]:
            for i in range(3): triangle.vertices[i*3+1]=triangle.vertices[i*3]*.2
        for _ in range(160):tick()
        print('Slope state',list(guest.position),guest.flags,guest.epoch,guest.hostFrame,host.frame,flush=True)
        assert guest.character==1 and guest.status&1 and guest.flags&8 and guest.epoch==224,('Slope landing',list(guest.position),guest.status,guest.flags,guest.epoch)
        assert abs(guest.position[1]-guest.position[0]*.2)<3,('Slope floor alignment',list(guest.position))
        host.stickY=80
        for _ in range(25):tick()
        host.stickY=0
        assert abs(guest.position[1]-guest.position[0]*.2)<3,('Uphill clipping',list(guest.position))
        assert guest.rotationX or guest.rotationZ,'Original slope rotation was not transmitted'
        results.append({'slope_landing_and_uphill_movement':'passed','rotationX':guest.rotationX,'rotationZ':guest.rotationZ})
        print('PASS native task plus streamed contact adapter: uphill collision and slope orientation',flush=True)
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
        results.append({'pause_resume_epoch_and_Link_yield':'passed'})
        print('PASS pause, scripted reposition, scene epoch and Link yield',flush=True)
        passed=True
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/native-physics-live-test.json').write_text(json.dumps({'version':'0.1.21','tested_dll_sha256':hashlib.sha256((args.sadx/'mods/TerminaAdventureBridge/TerminaAdventureSADX.dll').read_bytes()).hexdigest(),'status':'passed' if passed else 'failed','method':'Installed original SADX tasks with streamed collision/contact adapters and synthetic host packets','checks':results,'zelda_gameplay_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
