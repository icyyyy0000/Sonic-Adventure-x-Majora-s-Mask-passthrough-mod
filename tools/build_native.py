"""Build optional 64-bit recomp transport and 32-bit SADX observer with portable Zig."""
import argparse
import os
import subprocess
import shutil
import struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parents[1]/'work'

def restore_guest_018():
    """Camera-only builds retain the exact shipped 0.1.18 character engine."""
    old=ROOT/'release/0.1.18/observer/sadx/TerminaAdventureBridge/TerminaAdventureSADX.dll'
    current=ROOT/'build/native/TerminaAdventureSADX.dll'
    def sections(path):
        data=path.read_bytes();pe=struct.unpack_from('<I',data,0x3c)[0]
        count=struct.unpack_from('<H',data,pe+6)[0];size=struct.unpack_from('<H',data,pe+20)[0];result={}
        for i in range(count):
            pos=pe+24+size+i*40;name=data[pos:pos+8].split(b'\0')[0]
            length,_,_,start=struct.unpack_from('<IIII',data,pos+8)
            if name!=b'.buildid':result[name]=data[start:start+length]
        return result
    assert sections(current)==sections(old),'Companion implementation differs from 0.1.18; refusing to substitute it.'
    shutil.copy2(old,current)
    print('Restored exact 0.1.18 companion; rebuilt code/data sections match its baseline.')
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--zig',type=Path,default=WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe')
    p.add_argument('--sdk',type=Path,default=WORK/'sadx-mod-loader/SADXModLoader/include')
    p.add_argument('--restore-018-companion',action='store_true')
    args=p.parse_args()
    env=os.environ.copy()
    env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache')
    env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
    out=ROOT/'build/native'
    out.mkdir(parents=True,exist_ok=True)
    flags=['-std=c++17','-O2','-shared','-Iprotocol','-Inative','-fno-exceptions','-fno-rtti']
    targets=[('x86_64-windows-gnu', ['native/recomp_bridge.cpp','native/transport.cpp'],
              ['-Ioffline_build'], out/'termina_bridge.dll'),
             ('x86_64-windows-gnu', ['native/recomp_bridge.cpp','native/transport.cpp'],
              ['-Ioffline_build','-DTA_TEST_TRANSPORT'], out/'termina_bridge_test.dll'),
             ('x86-windows-gnu', ['guest/sadx_bridge.cpp','native/transport.cpp'],
              ['-I'+str(args.sdk),'-fms-extensions','-Wno-ignored-attributes'], out/'TerminaAdventureSADX.dll')]
    for target,files,extra,dest in targets:
        print(f'Building {dest.name}: {target}',flush=True)
        subprocess.run([str(args.zig),'c++','-target',target,*flags,*extra,*files,'-o',str(dest)],cwd=ROOT,env=env,check=True)
    subprocess.run([str(args.zig),'c++','-target','x86-windows-gnu','-O2','-DTA_TEST_TRANSPORT','-Iprotocol','-Inative',
                    'tests/guest_probe.cpp','native/transport.cpp','-o',str(out/'guest_probe.exe')],cwd=ROOT,env=env,check=True)
    subprocess.run([str(args.zig),'c++','-target','x86-windows-gnu','-std=c++17','-O2','-DTA_TEST_TRANSPORT','-Iprotocol','-Inative','-Iguest',
                    '-I'+str(args.sdk),'-fms-extensions','-Wno-ignored-attributes',
                    'tests/world_probe.cpp','native/transport.cpp','-o',str(out/'world_probe.exe')],cwd=ROOT,env=env,check=True)
    subprocess.run([str(args.zig),'c++','-target','x86-windows-gnu','-std=c++17','-O2','-Iguest',
                    '-I'+str(args.sdk),'-fms-extensions','-Wno-ignored-attributes',
                    'tests/character_select_probe.cpp','-o',str(out/'character_select_probe.exe')],cwd=ROOT,env=env,check=True)
    subprocess.run([str(args.zig),'cc','-target','x86-windows-gnu','-D_LANGUAGE_C','-DF3DEX_GBI_2',
                    '-DF3DEX_GBI_PL','-DGBI_DOWHILE','-Iinclude','-Imm-decomp/include',
                    'tests/render_addresses.c','-o',str(out/'render_addresses.exe')],cwd=ROOT,env=env,check=True)
    subprocess.run([str(args.zig),'cc','-target','x86-windows-gnu','-D_LANGUAGE_C','-DF3DEX_GBI_2',
                    '-DF3DEX_GBI_PL','-DGBI_DOWHILE','-Isrc','-Iinclude','-Imm-decomp/include',
                    'tests/render_visibility.c','-o',str(out/'render_visibility.exe')],cwd=ROOT,env=env,check=True)
    subprocess.run([str(args.zig),'cc','-target','x86-windows-gnu','-D_LANGUAGE_C','-DF3DEX_GBI_2',
                    '-DF3DEX_GBI_PL','-DGBI_DOWHILE','-Iinclude','-Imm-decomp/include',
                    'tests/collision_flags.c','-o',str(out/'collision_flags.exe')],cwd=ROOT,env=env,check=True)
    subprocess.run([str(args.zig),'c++','-target','x86-windows-gnu','-fno-exceptions','-fno-rtti','-Iprotocol','-Iguest',
                    'tests/world_contacts.cpp','-o',str(out/'world_contacts.exe')],cwd=ROOT,env=env,check=True)
    subprocess.run([str(args.zig),'c++','-target','x86-windows-gnu','-std=c++17','-Iguest',
                    '-I'+str(args.sdk),'-fms-extensions','-Wno-ignored-attributes',
                    'tests/owned_input.cpp','-o',str(out/'owned_input.exe')],cwd=ROOT,env=env,check=True)
    subprocess.run([str(args.zig),'c++','-target','x86-windows-gnu','-std=c++17','-Iguest',
                    '-I'+str(args.sdk),'-fms-extensions','-Wno-ignored-attributes',
                    'tests/native_audio.cpp','-o',str(out/'native_audio.exe')],cwd=ROOT,env=env,check=True)
    if args.restore_018_companion:restore_guest_018()
    print('Native companion and bridge compiled; run install_companion.py to deploy them.')
if __name__=='__main__': main()
