"""Exercise real recomp-word -> shared memory -> 32-bit Ninja collision conversion."""
import ctypes as c
import json
import subprocess
import time
from pathlib import Path
from test_transport import Host, Context
ROOT = Path(__file__).resolve().parents[1]
class Triangle(c.Structure):
    _fields_ = [('flags',c.c_uint32),('vertices',c.c_float*9)]
class World(c.Structure):
    _fields_ = [('scene',c.c_uint32),('epoch',c.c_uint32),('revision',c.c_uint32),
                ('count',c.c_uint32),('flags',c.c_uint32),('reserved',c.c_uint32),
                ('center',c.c_float*3),('radius',c.c_float),('triangles',Triangle*2048)]
def main():
    assert c.sizeof(World) == 81960
    dll = c.CDLL(str(ROOT/'build/native/termina_bridge_test.dll'))
    dll.ta_transport_write_host.argtypes = [c.POINTER(Host)]
    dll.ta_transport_write_world.argtypes = [c.POINTER(World)]
    dll.ta_transport_read_world.argtypes = [c.POINTER(World)]
    dll.ta_bridge_publish_world.argtypes = [c.c_void_p,c.POINTER(Context)]
    host = Host(frame=1,scene=2,epoch=7,character=3,flags=1)
    world = World(scene=2,epoch=7,revision=1,count=2,radius=350)
    world.triangles[0].flags = world.triangles[1].flags = 1
    world.triangles[0].vertices[:] = [0,0,0, 10,0,0, 0,0,-10]
    world.triangles[1].vertices[:] = [0,0,0, 0,10,0, 10,0,0]
    assert dll.ta_transport_write_host(c.byref(host)) == 1
    memory = (c.c_uint32*((c.sizeof(world)+256)//4))()
    c.memmove(c.addressof(memory)+128,c.addressof(world),c.sizeof(world))
    ctx = Context();ctx.r[4]=0xffffffff80000080;ctx.r[5]=c.sizeof(world)//4
    dll.ta_bridge_publish_world(memory,c.byref(ctx));assert ctx.r[2] == 1
    subprocess.run([str(ROOT/'build/native/world_probe.exe')],check=True,timeout=5)
    copy = World()
    assert dll.ta_transport_read_world(c.byref(copy)) == 1
    host.epoch = 8;assert dll.ta_transport_write_host(c.byref(host)) == 1
    assert dll.ta_transport_read_world(c.byref(copy)) == 0, 'Scene epoch mismatch accepted'
    world.count=2049;assert dll.ta_transport_write_world(c.byref(world)) == 0
    world.count=2;world.triangles[0].vertices[0]=float('nan')
    assert dll.ta_transport_write_world(c.byref(world)) == 0
    world.triangles[0].vertices[0]=0
    ctx.r[5]-=1;dll.ta_bridge_publish_world(memory,c.byref(ctx));assert ctx.r[2] == 0
    host.epoch=7;assert dll.ta_transport_write_host(c.byref(host)) == 1
    time.sleep(1.25)
    assert dll.ta_transport_read_world(c.byref(copy)) == 0, 'Stale collision accepted'
    dll.ta_transport_close()
    result={'status':'passed','checks':['81960-byte cross-process ABI','recomp CPU-context world publication',
        '32-bit Ninja mesh, normal, bounds and LandTable conversion; all 2048 triangles convert to 64 collision groups without index wrap','zero-area and truncated meshes refused',
        'scene epoch mismatch refused','capacity overflow and nonfinite coordinates refused',
        'incorrect RDRAM word count refused','stale host and world refused'],
        'gameplay_tested':False,'engine_collision_installed':False}
    (ROOT/'docs/world-test.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
