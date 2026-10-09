"""Run the production Gamma shot handler with controlled Zelda spawn/aim dependencies."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
source=(ROOT/'src/characters/sonic.c').read_text()
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
a=source.index('void ta_sonic_update(');b=source.index('static Actor* nativeTarget;',a);source=source[:a]+source[b:]
preamble=r"""
#include <math.h>
#include <assert.h>
#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include "bridge_protocol.h"
typedef float f32;typedef uint32_t u32;typedef int s32;
typedef struct {float x,y,z;} Vec3f;
typedef struct {int x,y,z;} Rot;
typedef int CollisionPoly;
#define ACTORCAT_MAX 12
#define ACTORCAT_ENEMY 5
#define ACTORCAT_BOSS 9
#define ACTOR_FLAG_ATTENTION_ENABLED 1
#define BGCHECKFLAG_GROUND 1
#define TA_SONIC 1
#define RECOMP_EXPORT
typedef struct Actor {void* update;unsigned flags;struct Actor* next;struct {unsigned health;} colChkInfo;struct {Vec3f pos;} world,focus;struct {Rot rot;} shape;unsigned bgCheckFlags;} Actor;
typedef struct {Actor actor;Actor* focusActor;} Player;
typedef struct {int colCtx;struct {struct {Actor* first;} actorLists[12];} actorCtx;Player* player;} PlayState;
#define GET_PLAYER(play) ((play)->player)
static struct {unsigned character;} ta_state={TA_SONIC};
static u32 ta_native_live=1;static TA_GuestFrame ta_native_pose;
static int blocked;
static int ta_can_control(Player* p,PlayState* play) {return p==play->player;}
static int BgCheck_EntityLineTest1(int* col,Vec3f* a,Vec3f* b,Vec3f* hit,CollisionPoly** poly,int x,int y,int z,int w,int* id) {return blocked;}
static int ta_sonic_target_point(Player* p,Actor* t,Vec3f* point,float* radius) {*point=t->focus.pos;if(point->y<t->world.pos.y+10)point->y=t->world.pos.y+15;*radius=10;return 1;}
static float Math_SinS(int yaw) {return sinf(yaw/10430.37835f);}
static float Math_CosS(int yaw) {return cosf(yaw/10430.37835f);}
"""
checks=r"""
int main() {
 Player p={0};PlayState play={0};play.player=&p;ta_sonic_play=&play;
 Actor a={0},b={0};a.update=b.update=(void*)1;a.flags=b.flags=1;a.colChkInfo.health=b.colChkInfo.health=3;
 a.world.pos.z=a.focus.pos.z=100;a.focus.pos.y=15;
 b.world.pos.z=b.focus.pos.z=60;b.focus.pos.y=15;
 play.actorCtx.actorLists[5].first=&a;
 TA_HostFrame packet={0};termina_adventure_get_sonic_target(&packet);
 assert(packet.flags&TA_HOST_HOMING_TARGET);assert(fabsf(packet.targetPosition[0]-100/2.8f)<.001f);u32 first=packet.targetId;
 // A newer target must not steal the identity of an already returned hit.
 a.next=&b;packet=(TA_HostFrame){0};termina_adventure_get_sonic_target(&packet);u32 second=packet.targetId;assert(second!=first);
 Vec3f hit;ta_native_pose.hitSequence=1;ta_native_pose.hitTargetId=first;
 assert(ta_sonic_native_hit(&p,&play,&hit)==1 && hit.z==100);
 assert(ta_sonic_native_hit(&p,&play,&hit)==0);
 packet=(TA_HostFrame){0};termina_adventure_get_sonic_target(&packet);assert(packet.targetId==second);
 // Removed actors are never dereferenced or damaged from delayed replies.
 a.next=0;ta_native_pose.action=14;packet=(TA_HostFrame){0};termina_adventure_get_sonic_target(&packet);assert(!packet.flags);
 ta_native_pose.hitSequence=2;ta_native_pose.hitTargetId=second;assert(!ta_sonic_native_hit(&p,&play,&hit));
 ta_sonic_native_reset();ta_native_pose.action=8;blocked=1;packet=(TA_HostFrame){0};termina_adventure_get_sonic_target(&packet);assert(!packet.flags);
 blocked=0;a.colChkInfo.health=0;packet=(TA_HostFrame){0};termina_adventure_get_sonic_target(&packet);assert(!packet.flags);
 a.colChkInfo.health=3;p.actor.bgCheckFlags=1;packet=(TA_HostFrame){0};termina_adventure_get_sonic_target(&packet);assert(packet.flags);
 ta_native_pose.hitSequence=3;ta_native_pose.hitTargetId=0xabcdef;assert(!ta_sonic_native_hit(&p,&play,&hit));
 puts("PASS: production homing target identity, chain retarget, hit deduplication, despawn safety, line of sight and dead-enemy rejection.");
}
"""
p=WORK/'sonic_targets_unit.c';p.write_text(preamble+source+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/sonic_targets_unit.exe'
subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc','-target','x86_64-windows-gnu','-I'+str(ROOT/'protocol'),str(p),'-o',str(exe)],env=env,check=True)
subprocess.run([str(exe)],check=True)
import json
(ROOT/'docs/sonic-targets-0.1.21.json').write_text(json.dumps({'status':'passed','checks':['production target selection','delayed hit retains target identity','chain retarget','deduplicated hits','despawn safety','line of sight','dead enemy rejection','unknown identity refusal'],'zelda_enemy_combat_verified':False},indent=2)+'\n')
