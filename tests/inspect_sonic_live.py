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
        for _ in range(60):tick()
        def show(label):
            print(label,'action',guest.action,'anim',guest.animation,'export',guest.actionIndex,'frame',guest.animationFrame,'status',hex(guest.status),'delta',list(guest.velocity),'pos',list(guest.position),flush=True)
        host.stickY=80
        for i in range(40):
            tick()
            if i%5==0:show('run '+str(i))
        host.stickY=0
        for i in range(15):tick();show('coast '+str(i))
        host.buttons=0x8000
        for i in range(4):tick();show('jump '+str(i))
        host.buttons=0
        for i in range(2):tick();show('air release '+str(i))
        host.buttons=0x8000
        for i in range(5):tick();show('air A '+str(i))
        host.buttons=0
        for _ in range(40):tick()
        host.buttons=0x4000
        for i in range(10):tick();show('charge '+str(i))
        host.buttons=0
        for i in range(15):tick();show('spindash '+str(i))
        passed=True
    finally:
        dll.ta_transport_close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (ROOT/'docs/sonic-baseline-0.1.5.json').write_text(json.dumps({'status':'passed' if passed else 'failed','method':'Installed original SADX tasks with streamed collision/contact adapters and synthetic host packets','checks':results,'zelda_gameplay_verified':False},indent=2)+'\n')
if __name__=='__main__':main()
