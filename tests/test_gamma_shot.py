"""Run the production Gamma shot handler with controlled Zelda spawn/aim dependencies."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
source=(ROOT/'src/characters/gamma.c').read_text()
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
preamble=r'''
#include <math.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef float f32;
#define BTN_A 0x8000
#define BTN_B 0x4000
#define BGCHECKFLAG_GROUND 1
#define ACTORCAT_ENEMY 5
#define ACTORCAT_BOSS 9
#define ACTOR_EN_ARROW 15
typedef struct {float x,y,z;} Vec3;
typedef struct {int x,y,z;} Rot;
typedef struct Actor {void* update;int category;struct {Vec3 pos;Rot rot;} world;struct {Rot rot;} shape;Vec3 velocity;int bgCheckFlags;} Actor;
typedef struct {Actor actor;Actor* focusActor;float fallStartHeight;} Player;
typedef struct {int actorCtx;} PlayState;
typedef struct {struct {unsigned button;} cur,press;} Input;
typedef struct {int flight,cooldown;} TA_State;
typedef struct EnArrow {Actor actor;void (*actionFunc)(struct EnArrow*,PlayState*);Vec3 unk_228;int unk_260;} EnArrow;
static unsigned ta_settings[14]={1,1,1,1,1,1500,6,1,100,1,100,100,12,100};
static EnArrow arrow;
static int spawned,failSpawn;static float shotSpeed;
static int Math_Atan2S(float y,float x) {return (int)(atan2f(y,x)*10430.37835f);}
static Actor* Actor_Spawn(int* ctx,PlayState* play,int id,float x,float y,float z,int rx,int ry,int rz,int params) {
 ++spawned;if(failSpawn)return 0;memset(&arrow,0,sizeof arrow);arrow.actor.world.pos=(Vec3){x,y,z};arrow.actor.world.rot=(Rot){rx,ry,rz};return &arrow.actor;
}
static void Actor_SetSpeeds(Actor* actor,float speed) {shotSpeed=speed;}
void func_8088ACE0(EnArrow* arrow,PlayState* play) {}
void ta_gamma_shoot(Player*,PlayState*,Input*,TA_State*);
'''
checks=r'''
int main() {
 Player p={0};PlayState play={0};Input in={0};TA_State state={0};
 p.actor.world.pos=(Vec3){100,20,300};p.actor.velocity.y=7;
 in.press.button=BTN_B;ta_gamma_shoot(&p,&play,&in,&state);
 assert(spawned==1 && state.cooldown==12 && shotSpeed==80);
 assert(arrow.actionFunc==func_8088ACE0 && arrow.unk_260==12);
 assert(arrow.actor.world.pos.x==100 && arrow.actor.world.pos.y==44 && arrow.actor.world.pos.z==300);
 assert(p.actor.velocity.y==7); // native shot routing does not override motion
 ta_gamma_shoot(&p,&play,&in,&state);assert(spawned==1);
 Actor target={0};target.update=(void*)1;target.category=ACTORCAT_ENEMY;target.world.pos=(Vec3){200,80,300};
 p.focusActor=&target;state.cooldown=0;ta_gamma_shoot(&p,&play,&in,&state);
 assert(spawned==2 && arrow.actor.world.rot.y>16000 && arrow.actor.world.rot.x<0);
 state.cooldown=0;in.press.button=0;ta_gamma_shoot(&p,&play,&in,&state);assert(spawned==2);
 failSpawn=1;in.press.button=BTN_B;ta_gamma_shoot(&p,&play,&in,&state);assert(spawned==3 && state.cooldown==12);
 state.cooldown=0;ta_settings[12]=2;ta_gamma_shoot(&p,&play,&in,&state);assert(state.cooldown==2);state.cooldown=0;ta_settings[12]=60;ta_gamma_shoot(&p,&play,&in,&state);assert(state.cooldown==60);
 puts("PASS: production Gamma B shot, native velocity preserved, cooldown, enemy aim and spawn failure.");
}
'''
p=WORK/'gamma_shot_unit.c';p.write_text(preamble+source+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/gamma_shot_unit.exe'
subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc','-target','x86_64-windows-gnu',str(p),'-o',str(exe)],env=env,check=True)
subprocess.run([str(exe)],check=True)
