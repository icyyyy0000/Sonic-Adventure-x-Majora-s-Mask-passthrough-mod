"""Run the production Gamma shot handler with controlled Zelda spawn/aim dependencies."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
source=(ROOT/'bridge/src/world.c').read_text()
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include') and not line.startswith('RECOMP_IMPORT'))
preamble=r"""
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "world_protocol.h"
typedef uint32_t u32;typedef float f32;typedef int s32;typedef uint16_t u16;
typedef struct {float x,y,z;} Vec3f;
typedef struct {short x,y,z;} Vec3s;
typedef struct {u16 flags_vIA,flags_vIB,vIC;} CollisionPoly;
typedef struct {int numPolygons;Vec3s* vtxList;CollisionPoly* polyList;} CollisionHeader;
typedef struct {CollisionHeader* colHeader;struct {int polyStartIndex;} dynaLookup;} BgActor;
#define BG_ACTOR_MAX 2
#define BGACTOR_IN_USE 1
#define BGACTOR_COLLISION_DISABLED 2
#define COLPOLY_IGNORE_ENTITY 0x2000
#define COLPOLY_VIA_FLAG_TEST(x,y) ((x)&(y))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
typedef struct {BgActor bgActors[2];int bgActorFlags[2];CollisionPoly* polyList;Vec3s* vtxList;} DynaCollisionContext;
typedef struct {struct {struct {Vec3f pos;} world;} actor;} Player;
typedef struct {int sceneId;struct {DynaCollisionContext dyna;CollisionHeader* colHeader;} colCtx;} PlayState;
static TA_WorldFrame published;
static int ta_bridge_publish_world(void* data,unsigned words) {assert(words==sizeof(published)/4);memcpy(&published,data,sizeof(published));return 1;}
"""
checks=r"""
int main() {
 Player p={0};PlayState play={0};play.sceneId=6;
 Vec3s vertices[6]={{800,0,-10},{820,0,10},{820,0,-10},{-10,0,-10},{10,0,10},{10,0,-10}};
 static CollisionPoly polys[3002];
 for(int i=0;i<3000;i++)polys[i]=(CollisionPoly){0,1,2};
 polys[3000]=polys[3001]=(CollisionPoly){3,4,5};
 CollisionHeader h={3002,vertices,polys};play.colCtx.colHeader=&h;
 ta_export_world(&p,&play,8,20);
 assert(published.scene==6 && published.epoch==8 && published.revision==20);
 assert(!(published.flags&TA_WORLD_TRUNCATED) && published.count==2);
 assert(published.radius<1000/2.8f && published.radius>10);
 assert(published.triangles[0].vertices[1]==0);
 // Dynamic geometry is included in the same complete adaptive query.
 CollisionPoly dynamicPoly={3,4,5};CollisionHeader dynamicHeader={1,vertices,&dynamicPoly};
 play.colCtx.dyna.bgActorFlags[0]=1;play.colCtx.dyna.bgActors[0].colHeader=&dynamicHeader;
 play.colCtx.dyna.polyList=&dynamicPoly;play.colCtx.dyna.vtxList=vertices;
 ta_export_world(&p,&play,8,21);assert(published.count==3 && published.triangles[0].flags&TA_SURFACE_DYNAMIC);
 // Extreme geometry that cannot fit even at minimum radius stays explicitly
 // unsafe; the companion's safe wait handles it rather than using a partial floor.
 for(int i=0;i<3000;i++)polys[i]=(CollisionPoly){3,4,5};
 ta_export_world(&p,&play,8,22);assert(published.flags&TA_WORLD_TRUNCATED);
 puts("PASS: production dense-world exporter shrinks to complete near geometry, retains dynamic floor and marks irreducible overflow unsafe.");
}
"""
p=WORK/'sonic_world_window_unit.c';p.write_text(preamble+source+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/sonic_world_window_unit.exe'
subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc','-target','x86_64-windows-gnu','-I'+str(ROOT/'protocol'),str(p),'-o',str(exe)],env=env,check=True)
subprocess.run([str(exe)],check=True)
