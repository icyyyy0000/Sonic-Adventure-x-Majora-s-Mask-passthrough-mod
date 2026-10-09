"""Read-only capture of the two-game bridge. Never publishes controls or packets."""
import ctypes as c,json,sys,time
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from test_transport import Host,Guest
from test_world import World
k=c.WinDLL('kernel32',use_last_error=True)
k.OpenFileMappingW.argtypes=[c.c_uint32,c.c_int,c.c_wchar_p];k.OpenFileMappingW.restype=c.c_void_p
k.MapViewOfFile.argtypes=[c.c_void_p,c.c_uint32,c.c_uint32,c.c_uint32,c.c_size_t];k.MapViewOfFile.restype=c.c_void_p
k.UnmapViewOfFile.argtypes=[c.c_void_p];k.CloseHandle.argtypes=[c.c_void_p]
k.GetTickCount64.restype=c.c_uint64
class Shared(c.Structure):_fields_=[('head',c.c_uint32*8),('host',Host),('guest',Guest)]
class WorldShared(c.Structure):_fields_=[('head',c.c_uint32*4),('world',World)]
def read(name,kind):
    handle=k.OpenFileMappingW(4,False,name) # FILE_MAP_READ: no new mappings/writes.
    if not handle:return None
    view=k.MapViewOfFile(handle,4,0,0,c.sizeof(kind))
    try:return kind.from_buffer_copy(c.string_at(view,c.sizeof(kind))) if view else None
    finally:
        if view:k.UnmapViewOfFile(view)
        k.CloseHandle(handle)
def main():
    print('Recording Sonic for 10 seconds. Try moving in Zelda and leave both games open.',flush=True)
    records=[]
    for _ in range(40):
        s=read('Local\\TerminaAdventure_v4',Shared)
        w=read('Local\\TerminaAdventure_World_v4',WorldShared)
        now=k.GetTickCount64()&0xffffffff
        row={'sample_time':datetime.now().astimezone().isoformat(),'mapping_present':bool(s)}
        if s:
            h=s.host;g=s.guest
            row['host']={'pid':s.head[3],'age_ms':(now-s.head[5])&0xffffffff,'frame':h.frame,
                'epoch':h.epoch,'scene':h.scene,'character':h.character,'flags':h.flags,
                'buttons':h.buttons,'stick':[h.stickX,h.stickY],'position':list(h.position),
                'gameplay_allowed':bool(h.flags&1),'native_requested':bool(h.flags&2),'paused':bool(h.flags&8)}
            row['guest']={'pid':s.head[4],'age_ms':(now-s.head[6])&0xffffffff,'frame':g.frame,
                'host_frame':g.hostFrame,'epoch':g.epoch,'scene':g.scene,'character':g.character,
                'flags':g.flags,'action':g.action,'position':list(g.position),'speed':list(g.nativeSpeed),
                'native_active':bool(g.flags&8),'status':g.status}
        if w:
            row['world']={'age_ms':(now-w.head[3])&0xffffffff,'epoch':w.world.epoch,
                'scene':w.world.scene,'revision':w.world.revision,'count':w.world.count,
                'flags':w.world.flags,'center':list(w.world.center),'radius':w.world.radius}
        records.append(row);time.sleep(.25)
    folder=ROOT/'docs/lock-captures';folder.mkdir(exist_ok=True)
    dest=folder/('sonic-lock-'+datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z')+'.json')
    dest.write_text(json.dumps({'build':'0.1.21','read_only':True,
        'note':'Unmodified live mappings; snapshots may straddle publication boundaries.','samples':records},indent=2)+'\n')
    print('Capture saved. Tell me "captured" in the chat so I can inspect it.\n'+str(dest),flush=True)
if __name__=='__main__':main()
