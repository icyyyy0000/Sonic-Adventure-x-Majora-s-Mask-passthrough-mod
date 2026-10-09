"""Exercise production Big gesture routing, collision cast and cross-game command."""
import os,subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
s=(ROOT/'src/characters/big.c').read_text();s=s[s.index('static u32 bigCommand'):s.index('void ta_big_update')]
preamble=r'''
#include <assert.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdbool.h>
#include "bridge_protocol.h"
typedef unsigned u32;typedef short s16;typedef int s32;typedef float f32;
typedef struct {float x,y,z;} Vec3f;
typedef struct {short x,y,z;} Vec3s;
typedef struct {Vec3f pos;} Position;
typedef struct {Position world;struct {Vec3s rot;} shape;unsigned bgCheckFlags;} Actor;
typedef struct {Actor actor;} Player,DynaPolyActor;
typedef struct {int dyna;} ColCtx;
typedef struct {ColCtx colCtx;} PlayState;
typedef struct {Vec3f at,eye;} Camera;
typedef struct {Vec3s normal;} CollisionPoly;
typedef struct {struct {unsigned button;int stick_x,stick_y;} cur,press;} Input;
typedef struct {int unused;} TA_State;
#define RECOMP_EXPORT
#define BTN_A 0x8000
#define BTN_B 0x4000
#define BTN_L 0x20
#define BTN_R 0x10
#define BTN_CUP 8
#define BGCHECKFLAG_GROUND 1
#define BGCHECK_SCENE -1
#define DMG_GORON_POUND 8
static unsigned ta_settings[16]={1,1,1,1,1,1500,6,1,100,1,100,100,12,100};static TA_GuestFrame ta_native_pose;
static Camera fixtureCamera={{0,24,10},{0,24,0}};
#define GET_ACTIVE_CAM(p) (&fixtureCamera)
static CollisionPoly surface={{0,0,-32767}};static Vec3f rayHit={0,24,1000};static int hit=1,attackCalls,dustCalls,casts,attackRadius;static DynaPolyActor platform;
static int geometricCast;static float minHeight=0,maxHeight=1000;
static Vec3f rayEnd;
static float Math_SinS(short yaw){return sinf(yaw*6.28318530718f/65536);}
static float Math_CosS(short yaw){return cosf(yaw*6.28318530718f/65536);}
static void Rumble_Request(float d,int power,int time,int decay){assert(power==180 && time==12);}
static int BgCheck_EntityLineTest2(ColCtx* ctx,Vec3f* start,Vec3f* end,Vec3f* result,CollisionPoly** poly,int wall,int floor,int ceiling,int face,s32* id,Actor* ignore){assert(wall&&floor&&ceiling&&!face);casts++;rayEnd=*end;if(!hit)return 0;
if(geometricCast){float dz=end->z-start->z;if(fabsf(dz)<.001)return 0;float t=(1000-start->z)/dz;if(t<0 || t>1)return 0;float y=start->y+(end->y-start->y)*t;if(y<minHeight || y>maxHeight)return 0;*result=(Vec3f){start->x+(end->x-start->x)*t,y,1000};}else *result=rayHit;*poly=&surface;*id=BGCHECK_SCENE;return 1;}
static int ta_mesh_line(PlayState* play,Vec3f* from,Vec3f* to,Vec3f* result,CollisionPoly** poly,s32* id){return BgCheck_EntityLineTest2(&play->colCtx,from,to,result,poly,1,1,1,0,id,NULL);}
static DynaPolyActor* DynaPoly_GetActor(ColCtx* ctx,int id){return &platform;}
static void ta_begin_attack(TA_State* s,int ticks,int radius,int offset,unsigned damage){assert(ticks==3 && damage==DMG_GORON_POUND);attackCalls++;attackRadius=radius;}
static void Actor_SpawnFloorDustRing(PlayState* play,Actor* actor,Vec3f* pos,int radius,int count,int accel,int scale,int step,int flag){dustCalls++;}
'''
checks=r'''
static void step(Player* p,PlayState* play,Input* in,TA_State* s){ta_big_capture_input(p,in);ta_big_native_update(p,play,in,s);}
static void air_tap(Player* p,PlayState* play,Input* in,TA_State* s){p->actor.bgCheckFlags=0;in->cur.button=in->press.button=BTN_B;step(p,play,in,s);assert(!bigMode && bigPending);in->cur.button=in->press.button=0;step(p,play,in,s);}
int main(){Player p={0};PlayState play={0};TA_State state={0};Input in={0};TA_HostFrame command={0};Vec3f endpoint;
 p.actor.bgCheckFlags=1;in.cur.button=in.press.button=BTN_B;step(&p,&play,&in,&state);
 termina_adventure_get_big_command(&command);assert(command.flags&TA_HOST_BIG_GRAPPLE);assert(command.targetRadius==6 && command.targetId && fabsf(command.targetPosition[0]-976/2.8f)<.01);
 assert(ta_big_line(&endpoint) && endpoint.z==1000);in.cur.button=in.press.button=BTN_A;step(&p,&play,&in,&state);assert(!ta_big_line(&endpoint));
 ta_big_reset();air_tap(&p,&play,&in,&state);assert(bigMode==1);
 ta_big_reset();p.actor.bgCheckFlags=0;in.cur.button=in.press.button=BTN_B;step(&p,&play,&in,&state);in.press.button=0;
 for(int i=0;i<4;i++){step(&p,&play,&in,&state);assert(!bigMode);}step(&p,&play,&in,&state);assert(bigMode==2 && !bigCastBuffer);
 for(int i=0;i<5;i++)step(&p,&play,&in,&state);assert(bigMode==2);in.cur.button=0;step(&p,&play,&in,&state);assert(bigMode==2);
 ta_big_reset();in.cur.button=in.press.button=BTN_B|BTN_R;step(&p,&play,&in,&state);in.press.button=0;for(int i=0;i<5;i++)step(&p,&play,&in,&state);assert(bigMode==2);
 ta_big_reset();in.cur.button=in.press.button=BTN_CUP;step(&p,&play,&in,&state);assert(!bigMode && !bigCastBuffer && !bigPending);
 ta_big_reset();p.actor.bgCheckFlags=1;hit=0;in.cur.button=in.press.button=BTN_B;step(&p,&play,&in,&state);assert(!bigMode && bigCastBuffer);hit=1;in.press.button=0;step(&p,&play,&in,&state);assert(bigMode==1);
 ta_big_reset();bigMode=2;ta_native_pose.hitTargetId=bigCommand;in.cur.button=in.press.button=0;ta_native_pose.renderFlags=TA_RENDER_BIG_IMPACT;ta_native_pose.hitSequence=1;step(&p,&play,&in,&state);step(&p,&play,&in,&state);assert(attackCalls==0 && dustCalls==1);Vec3f shock;for(int i=0;i<8;i++)assert(ta_big_shockwave(&shock));assert(!ta_big_shockwave(&shock));
 ta_big_reset();p.actor.shape.rot.y=0x4000;in.cur.button=in.press.button=BTN_B;step(&p,&play,&in,&state);assert(rayEnd.x>1400 && fabsf(rayEnd.z)<480 && rayEnd.y==96);
 ta_big_reset();in.cur.button=in.press.button=BTN_L;step(&p,&play,&in,&state);command=(TA_HostFrame){0};termina_adventure_get_big_command(&command);assert(command.flags&TA_HOST_BIG_EMOTE && ta_big_emote_frame()==1);
 in.cur.button=in.press.button=0;for(int i=0;i<10;i++)step(&p,&play,&in,&state);assert(ta_big_emote_frame()==11);in.cur.stick_y=80;step(&p,&play,&in,&state);assert(!ta_big_emote_frame());in.cur.stick_y=0;
 ta_big_reset();p.actor.shape.rot.y=0;geometricCast=1;minHeight=60;maxHeight=70;in.cur.button=in.press.button=BTN_B;step(&p,&play,&in,&state);assert(bigMode==1 && bigAnchor.y==68 && bigAnchor.z==1000);
 ta_big_reset();p.actor.shape.rot.y=(short)0x8000;step(&p,&play,&in,&state);assert(!bigMode);
 ta_big_reset();p.actor.shape.rot.y=0;p.actor.bgCheckFlags=0;geometricCast=0;in.cur.button=in.press.button=BTN_B;ta_big_capture_input(&p,&in);in.cur.button=in.press.button=0;ta_big_capture_input(&p,&in);for(int i=0;i<6;i++)ta_big_capture_input(&p,&in);assert(bigCastBuffer>0);ta_big_native_update(&p,&play,&in,&state);assert(bigMode==1 && !bigCastBuffer);
 ta_big_reset();hit=0;air_tap(&p,&play,&in,&state);assert(!bigMode && bigCastBuffer);hit=1;step(&p,&play,&in,&state);assert(bigMode==1);
 ta_big_reset();in.cur.button=in.press.button=BTN_B;step(&p,&play,&in,&state);in.press.button=0;for(int i=0;i<3;i++)step(&p,&play,&in,&state);p.actor.bgCheckFlags=1;step(&p,&play,&in,&state);assert(bigMode==1);
 ta_big_reset();bigCooldown=6;in.cur.button=in.press.button=BTN_B;step(&p,&play,&in,&state);assert(bigMode==1);
 ta_big_reset();ta_settings[9]=0;in.cur.button=in.press.button=BTN_B;step(&p,&play,&in,&state);assert(!bigMode && !bigPending);
 puts("PASS Big: ground B grapple, aerial tap/hold distinction, no C-Up, buffered retry, camera-independent casting, cancellation and unchanged impact");}
'''
p=WORK/'big_host_unit.c';p.write_text(preamble+s+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/big_host_unit.exe';subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc','-I'+str(ROOT/'protocol'),str(p),'-o',str(exe)],env=env,check=True);subprocess.run([str(exe)],check=True)
(ROOT/'docs/big-host-0.1.21.json').write_text(json.dumps({'version':'0.1.21','status':'passed','checks':['ground B immediately grapples','air B release before five updates grapples','air B hold five updates stomps once','R does not change B routing; C-Up does nothing','all-solid character-facing cast across four heights','A cancels','failed cast retries with buffered intent','impact produces one dust/rumble and eight shockwave frames','L wave cancels on stick','raised wall reached; wall behind character rejected','tap survives six unavailable updates','landing during hold grapples instead of stomping','fresh cast bypasses old cooldown','rod-only mode preserves original input'],'actual_in_game_grapple_aim_verified':False},indent=2)+'\n')
