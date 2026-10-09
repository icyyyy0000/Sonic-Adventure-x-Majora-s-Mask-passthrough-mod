"""Production camera fixtures with Zelda's actual integer angle table."""
import os,subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
source=(ROOT/'src/host/camera.c').read_text();source=source[source.index('// Only ordinary'):]
preamble=r'''
#include <assert.h>
#include <math.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#undef assert
#define assert(test) do {if(!(test)){fprintf(stderr,"Camera check failed at line %d: %s\n",__LINE__,#test);exit(1);}}while(0)
typedef unsigned short u16;typedef float f32;typedef short s16;typedef unsigned u32;typedef int s32;
typedef struct {float x,y,z;} Vec3f;
typedef struct {float r;s16 pitch,yaw;} VecGeo;typedef struct {int unused;} CollisionPoly;
typedef struct {int unk_64;} SwingAnimation;
typedef struct {struct {struct {struct {s16 y;} rot;} shape;struct {Vec3f pos;} world;} actor;} Player;
typedef struct {int sceneId,colCtx;Player* player;u32 gameplayFrames;} PlayState;
typedef struct {PlayState* play;int status,camId,mode,setting;void* target;void* focalActor;Vec3f at,eye,eyeNext;struct {s16 x,y,z;} inputDir;f32 dist,atLerpStepScale;Vec3f focalActorAtOffset;s16 roll;struct {struct {struct {f32 unk_00;s16 unk_20;} roData;} norm1;} paramData;} Camera;
#define RECOMP_HOOK(x)
#define RECOMP_HOOK_RETURN(x)
#define CAM_STATUS_ACTIVE 1
#define CAM_ID_MAIN 0
#define CAM_MODE_NORMAL 0
#define TA_LINK 0
#define GET_PLAYER(p) ((p)->player)
static unsigned ta_menu_open,ta_settings[16]={1,1,1,1,1,1500,6,1,100,1,100,100,12,100,0};
static int ta_native_owner=1,ta_native_visual=1,control=1,rayCalls;
static struct {u32 character;} ta_state={1};
#define BGCHECK_Y_MIN (-32000.0f)
static float wallDistance,floorY=BGCHECK_Y_MIN;
static int ta_can_control(Player* p,PlayState* play){return control;}
ANGLE_MATH
static Vec3f OLib_AddVecGeoToVec3f(Vec3f* at,VecGeo* geo){float yaw=geo->yaw*6.28318530718f/65536,pitch=geo->pitch*6.28318530718f/65536;return (Vec3f){at->x+sinf(yaw)*cosf(pitch)*geo->r,at->y+sinf(pitch)*geo->r,at->z+cosf(yaw)*cosf(pitch)*geo->r};}
static VecGeo OLib_Vec3fDiffToVecGeo(Vec3f* at,Vec3f* eye){Vec3f v={eye->x-at->x,eye->y-at->y,eye->z-at->z};float h=sqrtf(v.x*v.x+v.z*v.z);return (VecGeo){sqrtf(h*h+v.y*v.y),Math_Atan2S(v.y,h),Math_Atan2S(v.x,v.z)};}
static int BgCheck_CameraLineTest1(int* ctx,Vec3f* at,Vec3f* eye,Vec3f* hit,CollisionPoly** poly,int a,int b,int c,int id,int* bg){
 rayCalls++;if(!wallDistance)return 0;
 Vec3f v={eye->x-at->x,eye->y-at->y,eye->z-at->z};float d=sqrtf(v.x*v.x+v.y*v.y+v.z*v.z);
 if(d<wallDistance)return 0;
 *hit=(Vec3f){at->x+v.x*wallDistance/d,at->y+v.y*wallDistance/d,at->z+v.z*wallDistance/d};return 1;
}

static float Camera_GetFocalActorHeight(Camera* camera){return 48;}
static float BgCheck_CameraRaycastFloor2(int* ctx,CollisionPoly** poly,int* id,Vec3f* candidate){return floorY;}
'''
angle_math=(ROOT/'mm-decomp/src/code/sys_math_atan.c').read_text()
angle_math=angle_math[angle_math.index('u16 sATan2Tbl'):angle_math.index('f32 Math_Atan2F(')]
preamble=preamble.replace('ANGLE_MATH',angle_math)
checks=r'''
static void tick(Camera* c,int useSwing){
 c->play->gameplayFrames++;
 ta_camera_normal_enter(c);
 VecGeo candidate={100,0,0},old=candidate;SwingAnimation swing={0};
 if(useSwing){ta_camera_swing_enter(c,&candidate,&old,0,0,&swing,NULL);c->eye=c->eyeNext;ta_camera_swing_leave();}
 // Simulate stock speed/corner paths fighting yaw/pitch/roll after the swing.
 c->at.x=c->play->player->actor.world.pos.x-240;
 c->eye=c->eyeNext=(Vec3f){c->at.x+70,c->at.y+90,c->at.z-70};c->roll=9000;
 ta_camera_normal_leave();
}
static void reset(Camera* c,Player* p){
 followValid=cameraValid=0;wallDistance=0;floorY=BGCHECK_Y_MIN;
 p->actor.world.pos=(Vec3f){0,0,0};c->at=(Vec3f){0,0,0};c->eye=c->eyeNext=(Vec3f){0,0,100};c->dist=100;
 c->paramData.norm1.roData.unk_00=0;c->paramData.norm1.roData.unk_20=0;c->target=NULL;ta_menu_open=0;control=1;
}
int main(){
 Player p={0};PlayState play={17,0,&p};Camera c={.play=&play,.status=1,.focalActor=&p.actor};
 const s16 headings[]={0,1,-1,0x1fff,0x2000,0x2001,0x3fff,0x4000,0x4001,0x7fff,(s16)0x8000,(s16)0x8001,(s16)0xbfff,(s16)0xc000,(s16)0xc001};
 for(int setting=25;setting<=100;setting+=25)for(int ch=1;ch<=6;ch++)for(int h=0;h<15;h++){
  reset(&c,&p);ta_state.character=ch;ta_settings[14]=setting;p.actor.shape.rot.y=headings[h];
  for(int frame=0;frame<60;frame++){
   s16 before=followValid?orbit_angle(orbitYaw):0;
   p.actor.world.pos.x+=300;tick(&c,frame%2);
   assert(abs((s16)(orbit_angle(orbitYaw)-before))<=setting*65.536f+2);
   assert(c.at.x==p.actor.world.pos.x && c.at.z==p.actor.world.pos.z && c.roll==0);
   assert(fabsf(c.eye.y-c.at.y)<.01f && vector_length((Vec3f){c.eye.x-c.at.x,c.eye.y-c.at.y,c.eye.z-c.at.z})>1);
  }
  assert(abs((s16)(p.actor.shape.rot.y+0x8000-orbit_angle(orbitYaw)))<=300);
  assert(c.inputDir.y==orbit_angle(orbitYaw+0x8000));
  assert(fabsf(c.at.y-72)<.01f && fabsf(orbitDistance-140)<.01f);
 }
 for(int setting=50;setting<=100;setting+=25){
  reset(&c,&p);ta_settings[14]=setting;ta_state.character=1;
  for(int frame=0;frame<40;frame++){
   p.actor.shape.rot.y=frame%2?1:-1;s16 before=followValid?orbit_angle(orbitYaw):0;
   tick(&c,1);assert((s16)(orbit_angle(orbitYaw)-before)>=0); // No alternating +/-180 direction.
  }
  s16 stable=orbit_angle(orbitYaw);
  for(int frame=0;frame<20;frame++){p.actor.shape.rot.y=frame%2?80:-80;tick(&c,frame%2);assert(orbit_angle(orbitYaw)==stable);}
  f32 once=orbitYaw,height=orbitHeight,radius=contactRadius;
  ta_camera_normal_enter(&c);ta_camera_normal_leave();assert(orbitYaw==once && orbitHeight==height && contactRadius==radius);
 }
 reset(&c,&p);ta_settings[14]=100;p.actor.shape.rot.y=0x4000;tick(&c,1);
 wallDistance=20;tick(&c,1);assert(fabsf(contactRadius-12)<.01f);
 for(int i=0;i<20;i++){wallDistance=i%2?20:0;tick(&c,i%2);assert(contactRadius<12.01f);} // Grazing wall does not zoom in/out.
 wallDistance=0;tick(&c,1);tick(&c,1);tick(&c,1);assert(contactRadius>12 && contactRadius<40);
 for(int i=0;i<30;i++)tick(&c,1);assert(contactRadius>99);
 floorY=c.at.y+8;tick(&c,0);assert(c.eye.y>=floorY+5);floorY=BGCHECK_Y_MIN;
 // Modes that are not following do not take over stock normal results.
 for(int mode=0;mode<6;mode++){
  reset(&c,&p);ta_state.character=1;ta_settings[14]=100;
  if(mode==0)ta_state.character=0;if(mode==1)c.target=&p;if(mode==2)control=0;
  if(mode==3)ta_menu_open=1;if(mode==4)c.mode=1;if(mode==5)ta_settings[14]=0;
  tick(&c,0);assert(c.roll==9000 && c.eye.y==90 && c.at.x== -240);
  c.mode=0;
 }
 reset(&c,&p);ta_state.character=1;ta_settings[14]=100;ta_settings[1]=0;tick(&c,1);assert(c.roll==0);ta_settings[1]=1;
 // Teleports and backwards frame counters reset camera state safely.
 p.actor.world.pos.x+=2000;tick(&c,0);assert(c.at.x==p.actor.world.pos.x);
 play.gameplayFrames=0;tick(&c,1);assert(followFrame==1 && isfinite(c.eye.x));
 puts("PASS camera: all six guests, cardinal/diagonal/seam headings, 25/50/75/100 rates, half-turn stability, fast tracking, one final owner, level horizon, grazing-wall recovery, floor clearance and special-mode isolation.");
}
'''
p=WORK/'camera_unit.c';p.write_text(preamble+source+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/camera_unit.exe'
subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc','-target','x86_64-windows-gnu',str(p),'-o',str(exe)],env=env,check=True)
subprocess.run([str(exe)],check=True)
(ROOT/'docs/camera-0.1.22.json').write_text(json.dumps({'version':'0.1.22','status':'passed','checks':['six guests at fifteen cardinal/diagonal/signed-seam headings for 25/50/75/100 percent rates','180-degree target noise preserves turn direction','small heading noise stays in deadzone','300-unit-per-update horizontal tracking without reset/lag','normal/swing branch transitions have one final owner','duplicate same-frame callbacks do not advance angle, height or contact recovery','stock corner pitch and speed-induced roll do not affect guest orbit','grazing-wall flicker holds contact distance; stable clearance eases recovery','floor clearance retained','Link/target/script/menu/special mode/Off paths preserved','camera follow remains stable with obstacle smoothing Off','teleport and frame rollback reset safely'],'math':'actual Zelda Math_Atan2S integer lookup implementation','actual_zelda_camera_verified':False},indent=2)+'\n')
