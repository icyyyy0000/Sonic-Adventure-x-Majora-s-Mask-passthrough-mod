"""Exercise production emote state and pose without starting either game."""
import json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
state=(ROOT/'src/characters/emote.c').read_text();state=state[state.index('static u32'):]
pose=(ROOT/'src/render/emote_pose.h').read_text()
preamble=r'''
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#define assert(test) do {if(!(test)){fprintf(stderr,"Emote check failed at %d: %s\n",__LINE__,#test);exit(1);}}while(0)
typedef unsigned u32;typedef short s16;typedef int s32;typedef float f32;
typedef struct {s16 x,y,z;} Vec3s;
typedef struct {struct {unsigned bgCheckFlags;float speed;} actor;} Player;
typedef struct {int sceneId;unsigned gameplayFrames;} PlayState;
typedef struct {struct {unsigned button;int stick_x,stick_y;} cur,press;} Input;
#define TA_LINK 0
#define TA_SONIC 1
#define TA_TAILS 2
#define TA_KNUCKLES 3
#define TA_AMY 4
#define TA_BIG 5
#define TA_GAMMA 6
#define BTN_A 0x8000
#define BTN_B 0x4000
#define BTN_L 0x20
#define BGCHECKFLAG_GROUND 1
#define ABS(v) ((v)<0?-(v):(v))
static unsigned ta_menu_open,ta_native_live=1;
static struct {int character;} ta_state;
static struct {float nativeSpeed[3];} ta_native_pose;
static int control=1;
static int ta_can_control(Player* p,PlayState* play){return control;}
static float Math_SinS(short v){return sinf(v*6.28318530718f/65536);}
'''
checks=r'''
__declspec(dllexport) void preview_emote(unsigned character,int bone,int frame,Vec3s* rot){ta_emote_pose(character,bone,frame,rot);}
int main(){
 Player p={.actor={1,0}};PlayState play={1,100};Input in={0};
 for(int c=1;c<=6;c++){
  if(c==5)continue;ta_state.character=c;ta_emote_reset();in.cur.button=in.press.button=BTN_L;
  ta_emote_update(&p,&play,&in);assert(ta_emote_frame()==1);in.press.button=0;
  ta_emote_update(&p,&play,&in);assert(ta_emote_frame()==1);
  for(int i=1;i<40;i++){play.gameplayFrames++;ta_emote_update(&p,&play,&in);assert(ta_emote_frame()==i+1);}
  play.gameplayFrames++;ta_emote_update(&p,&play,&in);assert(!ta_emote_frame());
  play.gameplayFrames++;ta_emote_update(&p,&play,&in);assert(!ta_emote_frame()); // Held L never repeats.
  int changed=0;for(int bone=0;bone<128;bone++){Vec3s r={0};ta_emote_pose(c,bone,16,&r);changed+=r.x||r.y||r.z;
   if(bone<=1)assert(!r.x&&!r.y&&!r.z);Vec3s end={2,3,4};ta_emote_pose(c,bone,40,&end);assert(end.x==2&&end.y==3&&end.z==4);}
  assert(changed>=2);
 }
 ta_state.character=1;
 for(int reason=0;reason<8;reason++){
  ta_emote_reset();play.sceneId=1;play.gameplayFrames=100;in=(Input){0};in.cur.button=in.press.button=BTN_L;p.actor.bgCheckFlags=1;control=1;ta_menu_open=0;
  ta_emote_update(&p,&play,&in);assert(ta_emote_frame());in.press.button=0;
  if(reason==0)in.cur.stick_x=80;
  if(reason==1)in.cur.button=BTN_A;
  if(reason==2)in.cur.button=BTN_B;
  if(reason==3)p.actor.bgCheckFlags=0;
  if(reason==4)control=0;
  if(reason==5)ta_menu_open=1;
  if(reason==6)play.sceneId=2;
  if(reason==7)play.gameplayFrames=99;
  ta_emote_update(&p,&play,&in);assert(!ta_emote_frame());
 }
 p.actor.bgCheckFlags=1;control=1;ta_menu_open=0;play.gameplayFrames=100;in=(Input){0};in.cur.button=in.press.button=BTN_L;
 for(int c=0;c<=5;c+=5){ta_state.character=c;ta_emote_reset();ta_emote_update(&p,&play,&in);assert(!ta_emote_frame());}
 ta_state.character=1;ta_emote_reset();ta_native_pose.nativeSpeed[0]=2;ta_emote_update(&p,&play,&in);assert(!ta_emote_frame());ta_native_pose.nativeSpeed[0]=0;
 ta_emote_reset();ta_emote_update(&p,&play,&in);assert(ta_emote_frame());in.cur.button=in.press.button=0;ta_emote_update(&p,&play,&in);in.cur.button=in.press.button=BTN_L;ta_emote_update(&p,&play,&in);assert(!ta_emote_frame());
 puts("PASS five emotes: ground/idle trigger, held-L one-shot, duration, cancellation/isolation and safe canonical pose bones");
}
'''
f=WORK/'emote_unit.c';f.write_text(preamble+state+pose+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
zig=str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe')
exe=ROOT/'build/native/emote_unit.exe'
subprocess.run([zig,'cc',str(f),'-o',str(exe)],env=env,check=True);subprocess.run([str(exe)],check=True)
subprocess.run([zig,'cc','-shared',str(f),'-o',str(ROOT/'build/native/emote_pose_preview.dll')],env=env,check=True)
report={'version':'0.1.21','status':'passed','characters':['Sonic victory wave','Tails tail wag','Knuckles fist pump','Amy hammer salute','Gamma robot salute'],
'checks':['only five other guests start; Link excluded and Big wave retained','standing idle L triggers; held L never repeats','40 updates and repeated render samples do not change timing','stick A B airborne menu pause scene and frame rollback cancel','L cancels active emote','moving native task does not start emote','each canonical pose changes at least two intended bones; root and end pose unchanged'],
'actual_zelda_emotes_verified':False}
(ROOT/'docs/emotes-0.1.21.json').write_text(json.dumps(report,indent=2)+'\n')
