"""Exercise production host input routing, including override/scene-entry copies."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
source=(ROOT/'src/host/player.c').read_text()
helper=source[source.index('static void mask_foreign_input'):source.index('static ColliderCylinder attack;')]
common=source[source.index('RECOMP_HOOK("Player_UpdateCommon")'):source.index('RECOMP_HOOK_RETURN("Player_Update")')]
get=source[source.index('RECOMP_EXPORT void termina_adventure_get_input'):source.index('RECOMP_EXPORT u32 termina_adventure_gamma_speed')]
preamble=r'''
#include <assert.h>
#include <stdio.h>
typedef unsigned short u16;
#define TA_LINK 0
#define TA_BIG 5
#define BTN_L 0x20
#define BTN_A 0x8000
#define BTN_B 0x4000
#define BTN_R 0x10
#define BTN_CUP 8
#define BTN_CDOWN 4
#define BTN_CLEFT 2
#define BTN_CRIGHT 1
#define BTN_Z 0x2000
#define BTN_START 0x1000
#define PLAYER_STATE2_CAN_ACCEPT_TALK_OFFER 1
#define RECOMP_HOOK(x)
#define RECOMP_EXPORT
typedef struct {struct {unsigned button;int stick_x,stick_y;} cur,press,rel;} Input;
typedef struct {unsigned stateFlags2;} Player;
typedef struct {Player* player;} PlayState;
#define GET_PLAYER(p) ((p)->player)
static struct {int character;} ta_state;
static unsigned ta_native_owner,ta_menu_open,menuConsumed;
static Player* player;static PlayState* context;
static Input savedInput,abilityInput;
'''
checks=r'''
int main(){
 Player p={0},clone={0};PlayState play={&p};Input original={0},in;
 original.cur.button=original.press.button=original.rel.button=BTN_L|BTN_A|BTN_B|BTN_R|BTN_CUP|BTN_CDOWN|BTN_CLEFT|BTN_CRIGHT|BTN_Z|BTN_START;
 original.cur.stick_x=50;original.cur.stick_y=80;original.rel.stick_x=20;original.rel.stick_y=30;
 for(int character=1;character<=6;character++) {
  ta_state.character=character;ta_native_owner=1;in=original;
  ta_common_input(&p,&play,&in);
  assert(in.cur.button==(BTN_Z|BTN_START) && in.press.button==(BTN_Z|BTN_START));
  assert(in.rel.button==(BTN_Z|BTN_START) && in.cur.stick_x==0 && in.rel.stick_y==0);
  p.stateFlags2=1;in=original;ta_common_input(&p,&play,&in);assert(in.cur.button==(BTN_A|BTN_Z|BTN_START));p.stateFlags2=0;
 }
 ta_state.character=0;in=original;ta_common_input(&p,&play,&in);assert(in.cur.button==original.cur.button && in.cur.stick_y==80);
 ta_state.character=1;in=original;ta_common_input(&clone,&play,&in);assert(in.cur.button==original.cur.button);
 ta_native_owner=0;in=original;ta_common_input(&p,&play,&in);assert(in.cur.stick_y==80 && !(in.cur.button&BTN_B));
 player=&p;context=&play;abilityInput=original;savedInput=(Input){0};
 termina_adventure_get_input(&in);assert(in.cur.button==original.cur.button && in.cur.stick_y==80);
 ta_state.character=0;menuConsumed=1;in=original;ta_common_input(&p,&play,&in);assert(!in.cur.button && !in.cur.stick_y);menuConsumed=0;
 puts("PASS: whole roster masks final/override host attacks, shield and item inputs; contextual A, targeting, pause, Link and original ability input survive.");
}
'''
p=WORK/'host_input_unit.c';p.write_text(preamble+helper+common+get+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/host_input_unit.exe'
subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc','-target','x86_64-windows-gnu',str(p),'-o',str(exe)],env=env,check=True)
subprocess.run([str(exe)],check=True)
