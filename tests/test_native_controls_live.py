"""Exercise original SADX character tasks against a deliberately foreign floor.

Only our test game process is stopped; no Windows input is injected.
"""
import ctypes as c
import subprocess,time,json,argparse
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
        # Native task headings under the streamed coordinate basis.
        import math
        host.character=1;host.buttons=0;host.stickY=0
        for yaw in (0,16384,32768,49152):
            host.epoch+=1;world.epoch=host.epoch;host.position[:]=[100,50,170]
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
        host.position[:]=[100,50,170]
        for _ in range(60):tick()
        host.buttons=0x8000;flew=False
        for _ in range(12):
            tick();flew=flew or guest.action==15
        assert not flew,('Initial held jump entered flight',guest.action)
        host.buttons=0
        tick();tick()
        host.buttons=0x8000;peak=guest.position[1];flew=False;phases=[]
        for _ in range(30):
            tick();peak=max(peak,guest.position[1]);flew=flew or guest.action==15
            if guest.renderFlags&2:phases.append(guest.renderFlags>>16)
        assert flew and peak>35,('Second press failed flight',peak,guest.action)
        assert len(set(phases))>2,('Rotor phase did not advance',phases)
        host.buttons=0
        for _ in range(110):tick()
        assert guest.status&1,('Tails release landing',list(guest.position),guest.action)
        results.append({'held_jump_never_flies':True,'second_press_flies':True,'flight_peak':round(peak,3),'rotor_phases':len(set(phases)),'released_A_landed':True})
        host.epoch=world.epoch=222
        passed=True
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/native-controls-live-test.json').write_text(json.dumps({'status':'passed' if passed else 'failed','method':'Installed original SADX tasks with streamed collision/contact adapters and synthetic host packets','checks':results,'zelda_gameplay_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
