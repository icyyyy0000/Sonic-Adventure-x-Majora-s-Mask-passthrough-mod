"""Run the production Gamma shot handler with controlled Zelda spawn/aim dependencies."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
source=(ROOT/'src/host/player.c').read_text()
a=source.index('RECOMP_HOOK("Actor_UpdateVelocityWithGravity")');b=source.index('RECOMP_EXPORT void termina_adventure_select_character',a)
source=source[a:b]
preamble=r"""
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include "bridge_protocol.h"
#define RECOMP_HOOK(x)
#define TA_LINK 0
#define TA_SONIC 1
#define TA_TAILS 2
#define BGCHECKFLAG_GROUND 1
#define BGCHECKFLAG_CEILING 2
#define BTN_A 0x8000
#define PLAYER_STATE2_CAN_ACCEPT_TALK_OFFER 1
#define PLAYER_STATE1_8000000 1
#define ABS(x) abs(x)
typedef struct {float x,y,z;} Vec3f;
typedef struct Actor {float speed,gravity;Vec3f velocity;unsigned bgCheckFlags;} Actor;
typedef struct {Actor actor;float speedXZ;unsigned stateFlags1,stateFlags2;} Player;
typedef struct {int dummy;} PlayState;
typedef struct {int character,cooldown,jumpedThisFrame,flight,airJumpUsed,homingTicks,climbing,ticks;} TA_State;
typedef struct {struct {unsigned button;int stick_x,stick_y;} cur,press;} Input;
typedef struct {float jumpSpeed,runSpeed;void (*update)(Player*,PlayState*,Input*,TA_State*);} TA_CharacterDef;
static int calls,jumps;
static void prototype(Player* p,PlayState* play,Input* input,TA_State* state){calls++;}
static void ta_launch(Player* p,float speed){jumps++;p->actor.velocity.y=speed;}
static TA_CharacterDef ta_roster[3]={{0},{10,12,prototype},{10,12,prototype}};
static Player* player;static PlayState* context;static int applied;
static TA_State ta_state;static Input abilityInput;
static unsigned ta_native_live,ta_native_owner;static TA_GuestFrame ta_native_pose;
static int ta_can_control(Player* p,PlayState* play){return 1;}
"""
checks=r"""
int main(){
 Player p={0};PlayState play={0};player=&p;context=&play;
 ta_state.character=TA_SONIC;p.actor.gravity=-1;p.actor.bgCheckFlags=1;
 abilityInput.cur.stick_y=80;abilityInput.press.button=BTN_A;
 ta_native_owner=1;ta_native_live=0;p.actor.velocity=(Vec3f){2,-4,3};
 ta_before_motion(&p.actor);assert(calls==0 && jumps==0 && p.actor.velocity.x==0 && p.actor.velocity.y==1 && p.actor.velocity.z==0);
 applied=0;ta_native_live=1;ta_native_pose.character=TA_SONIC;
 ta_before_motion(&p.actor);assert(calls==0 && jumps==0);
 applied=0;ta_state.character=TA_TAILS;ta_native_live=0;ta_before_motion(&p.actor);assert(calls==0 && jumps==0);
 ta_state.character=TA_SONIC;
 // The old prototype is available only when original physics is explicitly off.
 applied=0;ta_native_owner=ta_native_live=0;ta_before_motion(&p.actor);assert(calls==1 && jumps==1);
 // Link progression remains under the original host controls.
 applied=0;ta_state.character=TA_LINK;ta_native_owner=1;ta_before_motion(&p.actor);assert(calls==1 && jumps==1);
 puts("PASS: production motion hook prevents Sonic fallback during reply loss, permits explicit physics-off and yields to Link.");
}
"""
p=WORK/'sonic_ownership_unit.c';p.write_text(preamble+source+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/sonic_ownership_unit.exe'
subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc','-target','x86_64-windows-gnu','-I'+str(ROOT/'protocol'),str(p),'-o',str(exe)],env=env,check=True)
subprocess.run([str(exe)],check=True)
