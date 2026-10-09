"""Real 64-bit DLL <-> 32-bit process test, including recomp pointer/word ABI."""
import ctypes as c
import json
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class Host(c.Structure):
    _fields_=[('frame',c.c_uint32),('scene',c.c_uint32),('epoch',c.c_uint32),('character',c.c_uint32),
             ('flags',c.c_uint32),('buttons',c.c_uint32),('stickX',c.c_int32),('stickY',c.c_int32),
             ('position',c.c_float*3),('velocity',c.c_float*3),('floorHeight',c.c_float),
             ('floorNormal',c.c_float*3),('grounded',c.c_uint32),('yaw',c.c_uint32),('cameraYaw',c.c_uint32),('targetId',c.c_uint32),('targetPosition',c.c_float*3),('targetRadius',c.c_float)]
class Guest(c.Structure):
    _fields_=[('frame',c.c_uint32),('character',c.c_uint32),('flags',c.c_uint32),('action',c.c_uint32),
             ('position',c.c_float*3),('velocity',c.c_float*3),('animationFrame',c.c_float),
             ('yaw',c.c_uint32),('status',c.c_uint32),('animation',c.c_uint32),('scene',c.c_uint32),('epoch',c.c_uint32),('hostFrame',c.c_uint32),('rotationX',c.c_uint32),('rotationZ',c.c_uint32),('actionIndex',c.c_uint32),('modelOffsetY',c.c_float),('previousActionIndex',c.c_uint32),('previousAnimationFrame',c.c_float),('animationBlend',c.c_float),('hitSequence',c.c_uint32),('hitTargetId',c.c_uint32),('nativeSpeed',c.c_float*3),('renderAnimation',c.c_uint32),('renderFlags',c.c_uint32)]
class Context(c.Structure):
    _fields_=[('r',c.c_uint64*32),('f',c.c_uint64*32),('hi',c.c_uint64),('lo',c.c_uint64),
             ('f_odd',c.c_void_p),('status',c.c_uint32),('mips3_float_mode',c.c_uint8)]

def main():
    assert c.sizeof(Host)==104 and c.sizeof(Guest)==124
    production=c.CDLL(str(ROOT/'build/native/termina_bridge.dll'))
    assert c.c_uint32.in_dll(production,'recomp_api_version').value==1
    dll=c.CDLL(str(ROOT/'build/native/termina_bridge_test.dll'))
    assert c.c_uint32.in_dll(dll,'recomp_api_version').value==1,'Runtime-required native mod API export missing or unsupported'
    for name,ty in [('ta_transport_write_host',Host),('ta_transport_read_guest',Guest)]:
        f=getattr(dll,name); f.argtypes=[c.POINTER(ty)]; f.restype=c.c_int
    for name in ['ta_bridge_publish','ta_bridge_poll']:
        f=getattr(dll,name);f.argtypes=[c.c_void_p,c.POINTER(Context)];f.restype=None
    ctx=Context()
    memory=(c.c_uint32*1024)()
    dll.ta_bridge_next_epoch.argtypes=[c.c_void_p,c.POINTER(Context)]
    dll.ta_bridge_next_epoch(memory,c.byref(ctx));first_epoch=ctx.r[2]&0xffffffff
    dll.ta_bridge_next_epoch(memory,c.byref(ctx));second_epoch=ctx.r[2]&0xffffffff
    assert first_epoch and second_epoch and first_epoch!=second_epoch
    host=Host(frame=123,character=3,flags=1)
    host.position[:]=[4.0,12.5,-6.0]
    c.memmove(c.addressof(memory)+256,c.addressof(host),c.sizeof(host))
    ctx.r[4]=0xffffffff80000100;ctx.r[5]=26
    dll.ta_bridge_publish(memory,c.byref(ctx))
    assert ctx.r[2]==1,'Publish through recomp CPU context failed'
    child=subprocess.Popen([str(ROOT/'build/native/guest_probe.exe')])
    try:
        guest=Guest()
        deadline=time.monotonic()+5
        while not dll.ta_transport_read_guest(c.byref(guest)) and time.monotonic()<deadline:time.sleep(0.01)
        assert guest.frame==456 and guest.character==3 and guest.animation==17
        assert abs(guest.modelOffsetY-2.85)<.001 and guest.previousActionIndex==82
        assert guest.previousAnimationFrame==7.5 and guest.animationBlend==.25
        assert list(guest.position)==[6.0,12.5,-9.0]
        ctx.r[4]=0xffffffff80000200;ctx.r[5]=31
        dll.ta_bridge_poll(memory,c.byref(ctx))
        assert ctx.r[2]==1
        copy=Guest.from_buffer_copy(bytes(memory)[512:636])
        assert copy.frame==456 and copy.position[1]==12.5
        # Bad pointer and incorrect word counts must fail without touching RDRAM.
        ctx.r[4]=0x100;dll.ta_bridge_poll(memory,c.byref(ctx));assert ctx.r[2]==0
        ctx.r[4]=0xffffffff80000200;ctx.r[5]=13
        dll.ta_bridge_poll(memory,c.byref(ctx));assert ctx.r[2]==0
        assert child.wait(timeout=5)==0,'32-bit probe failed'
        time.sleep(1.25)
        assert dll.ta_transport_read_guest(c.byref(guest))==0,'Crashed guest heartbeat remained live'
        # Restore a fresh snapshot, then abandon the mutex from a separate process.
        dll.ta_transport_write_guest.argtypes=[c.POINTER(Guest)]
        dll.ta_transport_write_guest.restype=c.c_int
        assert dll.ta_transport_write_guest(c.byref(guest))==1
        abandoned=subprocess.run([str(ROOT/'build/native/guest_probe.exe'),'--abandon'],timeout=5)
        assert abandoned.returncode==0
        assert dll.ta_transport_read_guest(c.byref(guest))==0,'Partial snapshot survived abandoned lock'
        result={'status':'passed','checks':['runtime-required recomp_api_version data export','native scene epochs are nonzero and advance','32/64-bit ABI sizes','host publication through recomp CPU context',
                'separate 32-bit guest reads host','guest reply received by 64-bit host',
                'word-order and float preservation in RDRAM','invalid pointers and lengths rejected',
                'guest crash heartbeat expires','abandoned mutex invalidates potentially torn snapshots'], 'gameplay_tested':False}
        (ROOT/'docs/transport-test-results.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
    finally:
        if child.poll() is None:child.terminate();child.wait()
        dll.ta_transport_close()
if __name__=='__main__':main()
