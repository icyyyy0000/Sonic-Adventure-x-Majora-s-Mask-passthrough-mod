"""Verify guest blur suppression and restoration using the stock status logic."""
import json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
source=(ROOT/'src/render/motion_blur.c').read_text();source=source[source.index('static int blurSuppressed'):]
stock=(ROOT/'mm-decomp/src/code/z_play.c').read_text(encoding='utf-8')
start=stock.index('    if (R_MOTION_BLUR_PRIORITY_ENABLED)',stock.index('void Play_DrawMotionBlur('))
end=stock.index('    if (sMotionBlurStatus != MOTION_BLUR_OFF)',start)
status=stock[start:end]
preamble=r'''
#include <assert.h>
#include <stdio.h>
typedef short s16;typedef struct {int unused;} Player;typedef struct {Player player;} PlayState;
#define RECOMP_HOOK(x)
#define RECOMP_HOOK_RETURN(x)
#define TA_LINK 0
#define GET_PLAYER(p) (&(p)->player)
#define R_MOTION_BLUR_ENABLED enabled
#define R_MOTION_BLUR_PRIORITY_ENABLED priority
#define R_MOTION_BLUR_ALPHA normalAlpha
#define R_MOTION_BLUR_PRIORITY_ALPHA priorityAlpha
#define MOTION_BLUR_OFF 0
#define MOTION_BLUR_SETUP 1
#define MOTION_BLUR_PROCESS 2
static int enabled=1,priority=1,normalAlpha=180,priorityAlpha=100,sMotionBlurStatus=2,blends;
static int ta_native_owner=1,ta_native_visual=1,control=1;
static struct {int character;} ta_state={1};
static int ta_can_control(Player* p,PlayState* play){return control;}
'''
checks=r'''
static void frame(PlayState* play){ta_motion_blur_enter(play);stock_status();ta_motion_blur_leave();}
int main(){
 PlayState play={0};
 for(int ch=1;ch<=6;ch++){
  ta_state.character=ch;enabled=priority=1;sMotionBlurStatus=2;blends=0;
  frame(&play);assert(!blends && sMotionBlurStatus==0 && enabled==1 && priority==1);
  assert(normalAlpha==180 && priorityAlpha==100);
 }
 // Returning to Link rebuilds the history instead of using a stale guest image.
 ta_state.character=0;frame(&play);assert(!blends && sMotionBlurStatus==2);
 frame(&play);assert(blends==1);
 ta_state.character=1;control=0;frame(&play);assert(blends==2 && enabled && priority);
 control=1;ta_native_visual=0;frame(&play);assert(blends==3);
 ta_native_visual=1;ta_native_owner=0;frame(&play);assert(blends==4);
 ta_native_owner=1;enabled=priority=0;frame(&play);assert(!enabled && !priority && sMotionBlurStatus==0);
 ta_motion_blur_enter(NULL);ta_motion_blur_leave();assert(!enabled && !priority);
 puts("PASS guest afterimage suppression: both blur requests, six characters, history reset, Link/cutscene/fallback isolation and exact request/alpha restoration.");
}
'''
p=WORK/'motion_blur_unit.c'
p.write_text(preamble+source+'\nstatic void stock_status(void){int alpha;\n'+status+'if(sMotionBlurStatus==MOTION_BLUR_PROCESS)blends++;else if(sMotionBlurStatus==MOTION_BLUR_SETUP)sMotionBlurStatus=MOTION_BLUR_PROCESS;\n}\n'+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/motion_blur_unit.exe'
subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc',str(p),'-o',str(exe)],env=env,check=True)
subprocess.run([str(exe)],check=True)
(ROOT/'docs/motion-blur-0.1.22.json').write_text(json.dumps({'version':'0.1.22','status':'passed','checks':['ordinary guest draws suppress both normal and priority blur','stock framebuffer history resets before returning to Link','all six characters covered','Link, cutscene/control loss, missing visual and native owner paths retain stock blur','blur enable requests and alpha values preserved'],'actual_zelda_trail_visually_verified':False},indent=2)+'\n')
