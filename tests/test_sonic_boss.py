"""Run the production Gamma shot handler with controlled Zelda spawn/aim dependencies."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
source=(ROOT/'src/characters/sonic_boss.c').read_text()
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
preamble=r"""
#include <math.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
#undef assert
#define assert(x) do {if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1;}} while(0)
typedef float f32;typedef int s32;typedef uint32_t u32;typedef uint8_t u8;
typedef struct {float x,y,z;} Vec3f;typedef struct {short x,y,z;} Vec3s;
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define CLAMP(x,a,b) MIN(MAX(x,a),b)
#define ACTOR_BOSS_HAKUGIN 0x1dd
#define ACTORCAT_BOSS 9
#define ACTOR_FLAG_ATTENTION_ENABLED 1
#define COLSHAPE_JNTSPH 0
#define ACELEM_ON 1
#define DMG_SWORD 0x200
#define DMG_GORON_SPIKES 0x4000
typedef struct Actor {int id;void* update;unsigned flags;struct Actor* next;struct {int health;} colChkInfo;struct {Vec3f pos;} world,focus;} Actor;
typedef struct {Actor actor;} Player;
typedef struct {struct {struct {Actor* first;} actorLists[12];} actorCtx;} PlayState;
typedef struct {struct {unsigned acElemFlags;} base;struct {struct {Vec3s center;short radius;} worldSphere;} dim;} ColliderJntSphElement;
typedef struct {struct {Actor* actor;int shape;} base;int count;ColliderJntSphElement* elements;} ColliderJntSph;
"""
checks=r"""
int main(){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
 Player p={0};PlayState play={0};assert(ta_sonic_damage_flags(&p,&play)==DMG_SWORD);
 Actor* boss=calloc(1,0x600);boss->id=ACTOR_BOSS_HAKUGIN;boss->update=(void*)1;boss->flags=1;boss->colChkInfo.health=30;
 boss->world.pos.x=100;boss->focus.pos=(Vec3f){400,300,0};play.actorCtx.actorLists[9].first=boss;
 assert(ta_sonic_damage_flags(&p,&play)==DMG_GORON_SPIKES);
 boss->colChkInfo.health=0;assert(ta_sonic_damage_flags(&p,&play)==DMG_SWORD);boss->colChkInfo.health=30;
 ColliderJntSph* col=(ColliderJntSph*)((u8*)boss+0x484);ColliderJntSphElement elements[19]={0};
 col->base.actor=boss;col->count=19;col->elements=elements;
 elements[0].base.acElemFlags=1;elements[0].dim.worldSphere.center=(Vec3s){100,80,0};elements[0].dim.worldSphere.radius=40;
 elements[5].base.acElemFlags=1;elements[5].dim.worldSphere.center=(Vec3s){80,20,0};elements[5].dim.worldSphere.radius=20;
 Vec3f point;float radius;assert(ta_sonic_target_point(&p,boss,&point,&radius));assert(point.y<40 && point.x<100 && radius>=5 && radius<=15);
 col->count=18;assert(!ta_sonic_target_point(&p,boss,&point,&radius));col->count=19;
 elements[0].base.acElemFlags=elements[5].base.acElemFlags=0;assert(!ta_sonic_target_point(&p,boss,&point,&radius));
 boss->id=1;assert(ta_sonic_target_point(&p,boss,&point,&radius) && point.x==400 && point.y==300);
 free(boss);puts("PASS: production boss spike profile, Goht body-sphere targeting, dead boss, invalid collider and ordinary enemy compatibility.");
}
"""
p=WORK/'sonic_boss_unit.c';p.write_text(preamble+source+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/sonic_boss_unit.exe'
subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc','-target','x86-windows-gnu',str(p),'-o',str(exe)],env=env,check=True)
subprocess.run([str(exe)],check=True,timeout=15)
import json,re
boss=(ROOT/'mm-decomp/src/overlays/actors/ovl_Boss_Hakugin/z_boss_hakugin.c').read_text()
assert re.search(r'/\* Sword\s+\*/ DMG_ENTRY\(1, GOHT_DMGEFF_DOWNED_ONLY\)',boss)
assert re.search(r'/\* Goron spikes\s+\*/ DMG_ENTRY\(1, GOHT_DMGEFF_GORON_SPIKES\)',boss)
assert 'this->actor.colChkInfo.damageEffect == GOHT_DMGEFF_GORON_SPIKES' in boss
(ROOT/'docs/sonic-boss-0.1.21.json').write_text(json.dumps({'status':'passed','checks':['production boss spike damage profile','Goht nearest enabled collision sphere','dead boss and invalid body collider refusal','ordinary enemy sword compatibility','verified Goht original damage table accepts spikes while running and sword only while downed'],'actual_boss_fight_verified':False},indent=2)+'\n')
