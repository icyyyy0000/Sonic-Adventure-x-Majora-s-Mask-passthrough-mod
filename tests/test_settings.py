"""Exercise the production settings input logic and native persistence ABI."""
import ctypes as c,json,os,subprocess
from pathlib import Path
from test_transport import Context
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
s=(ROOT/'src/host/settings.c').read_text();s=s[s.index('u32 ta_menu_open'):s.index('void ta_menu_draw')]
preamble=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef unsigned u32;typedef struct {int csAction;unsigned stateFlags1;} Player;
typedef struct {Player* player;struct {int state;} pauseCtx,csCtx;struct {int msgMode;} msgCtx;int transitionTrigger;} PlayState;
#define GET_PLAYER(p) ((p)->player)
#define PAUSE_STATE_OFF 0
#define CS_STATE_IDLE 0
#define PLAYER_CSACTION_NONE 0
#define TRANS_TRIGGER_OFF 0
#define MSGMODE_NONE 0
#define PLAYER_STATE1_DEAD 1
typedef struct {struct {unsigned button;} cur,press;} Input;
#define BTN_Z 0x2000
#define BTN_R 0x10
#define BTN_DDOWN 0x400
#define BTN_DUP 0x800
#define BTN_DLEFT 0x200
#define BTN_DRIGHT 0x100
#define BTN_A 0x8000
#define BTN_B 0x4000
#define BTN_START 0x1000
static int control=1,saves,resets;
static struct {int attackTicks;} ta_state;
static int ta_can_control(Player* p,PlayState* play){return control;}
static void ta_big_reset(void){resets++;}
static unsigned recomp_get_config_u32(const char* key){return 1;}
static unsigned ta_settings_load(void* p,unsigned count){return 1;}
static unsigned ta_settings_save(void* p,unsigned count){assert(count==16);saves++;return 1;}
'''
checks=r'''
int main(){
 Player p={0};PlayState play={.player=&p};Input in={0};ta_menu_init();assert(ta_settings[12]==12 && ta_settings[5]==1500 && ta_settings[6]==6);assert(sizeof(gammaFireTicks)/sizeof(gammaFireTicks[0])==5 && gammaFireTicks[0]==60 && gammaFireTicks[4]==2);assert(!strcmp(gammaFireNames[0],"Slowest") && !strcmp(gammaFireNames[4],"Fastest"));
 initialized=0;ta_settings[13]=137;ta_settings[11]=63;ta_settings[12]=4;ta_menu_init();assert(ta_settings[13]==125 && ta_settings[11]==75 && ta_settings[12]==6);
 initialized=0;ta_settings[12]=100;ta_menu_init();assert(ta_settings[12]==12 && ta_settings[5]==1500 && ta_settings[6]==6);assert(sizeof(gammaFireTicks)/sizeof(gammaFireTicks[0])==5 && gammaFireTicks[0]==60 && gammaFireTicks[4]==2);assert(!strcmp(gammaFireNames[0],"Slowest") && !strcmp(gammaFireNames[4],"Fastest"));
 in.cur.button=BTN_DDOWN;in.press.button=0;control=0;ta_menu_update(&p,&play,&in);assert(!ta_menu_open);
 in.cur.button=BTN_Z|BTN_DDOWN;ta_menu_update(&p,&play,&in);assert(ta_menu_open && resets==1);
 for(int i=0;i<15;i++)ta_menu_update(&p,&play,&in);assert(ta_menu_open && resets==1);
 in.cur.button=0;in.press.button=BTN_DUP;ta_menu_update(&p,&play,&in);assert(row==15);
 row=10;in.press.button=BTN_DRIGHT;for(int i=0;i<30;i++)ta_menu_update(&p,&play,&in);assert(ta_settings[8]==500);
 in.press.button=BTN_DLEFT;for(int i=0;i<20;i++)ta_menu_update(&p,&play,&in);assert(ta_settings[8]==25);
 initialized=0;ta_settings[5]=1900;ta_menu_init();assert(ta_settings[5]==2000);
 row=14;ta_settings[5]=600;in.press.button=BTN_DRIGHT;for(int i=1;i<5;i++){ta_menu_update(&p,&play,&in);assert(ta_settings[5]==grappleRanges[i]);}assert(!strcmp(grappleRangeNames[2],"Normal"));
 row=14;in.press.button=BTN_DRIGHT;for(int i=0;i<20;i++)ta_menu_update(&p,&play,&in);assert(ta_settings[5]==2400);
 initialized=0;ta_settings[6]=5;ta_menu_init();assert(ta_settings[6]==4);
 row=15;ta_settings[6]=3;in.press.button=BTN_DRIGHT;for(int i=1;i<5;i++){ta_menu_update(&p,&play,&in);assert(ta_settings[6]==grappleSpeeds[i]);}assert(!strcmp(grappleSpeedNames[2],"Normal"));
 row=15;in.press.button=BTN_DLEFT;for(int i=0;i<20;i++)ta_menu_update(&p,&play,&in);assert(ta_settings[6]==3);
 row=5;in.press.button=BTN_A;ta_menu_update(&p,&play,&in);assert(!ta_settings[2]);
 row=12;in.press.button=BTN_DRIGHT;for(int i=0;i<20;i++)ta_menu_update(&p,&play,&in);assert(ta_settings[10]==300);
 row=8;in.press.button=BTN_DLEFT;for(int i=0;i<20;i++)ta_menu_update(&p,&play,&in);assert(ta_settings[11]==25);
 row=13;in.press.button=BTN_A;ta_menu_update(&p,&play,&in);assert(!ta_settings[9]);
 row=7;ta_settings[13]=25;in.press.button=BTN_DRIGHT;for(int i=1;i<12;i++){ta_menu_update(&p,&play,&in);assert(ta_settings[13]==25*(i+1));}ta_menu_update(&p,&play,&in);assert(ta_settings[13]==300);
 row=8;ta_settings[11]=25;for(int i=1;i<12;i++){ta_menu_update(&p,&play,&in);assert(ta_settings[11]==25*(i+1));}
 row=11;ta_settings[12]=60;in.press.button=BTN_DRIGHT;for(int i=1;i<5;i++){ta_menu_update(&p,&play,&in);assert(ta_settings[12]==gammaFireTicks[i]);}ta_menu_update(&p,&play,&in);assert(ta_settings[12]==2);in.press.button=BTN_DLEFT;for(int i=3;i>=0;i--){ta_menu_update(&p,&play,&in);assert(ta_settings[12]==gammaFireTicks[i]);}ta_menu_update(&p,&play,&in);assert(ta_settings[12]==60);assert(gammaFireNames[2][0]=='N');
 row=1;in.press.button=BTN_A;ta_menu_update(&p,&play,&in);assert(!ta_settings[15] && ta_settings[0]);
 row=4;ta_settings[14]=0;in.press.button=BTN_DRIGHT;for(int i=1;i<=4;i++){ta_menu_update(&p,&play,&in);assert(ta_settings[14]==25*i);}ta_menu_update(&p,&play,&in);assert(ta_settings[14]==100);
 in.cur.button=in.press.button=BTN_B;ta_menu_update(&p,&play,&in);assert(!ta_menu_open && saves==1 && !in.press.button);
 in.cur.button=0;in.press.button=0;ta_menu_update(&p,&play,&in);play.pauseCtx.state=1;in.cur.button=BTN_Z|BTN_DDOWN;ta_menu_update(&p,&play,&in);assert(!ta_menu_open);
 in.cur.button=0;ta_menu_update(&p,&play,&in);play.pauseCtx.state=0;in.cur.button=BTN_Z;ta_menu_update(&p,&play,&in);in.cur.button|=BTN_DDOWN;ta_menu_update(&p,&play,&in);assert(ta_menu_open);
 in.cur.button=0;in.press.button=BTN_B;ta_menu_update(&p,&play,&in);in.press.button=0;in.cur.button=BTN_R|BTN_DDOWN;ta_menu_update(&p,&play,&in);assert(ta_menu_open);
 puts("PASS settings navigation, bounded sliders, audio toggle, save/close input consumption");
}
'''
p=WORK/'settings_unit.c';p.write_text(preamble+s+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/settings_unit.exe';subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc',str(p),'-o',str(exe)],env=env,check=True);subprocess.run([str(exe)],check=True)
dll=c.CDLL(str(ROOT/'build/native/termina_bridge_test.dll'));memory=(c.c_uint32*128)();ctx=Context();ctx.r[4]=0xffffffff80000000;ctx.r[5]=16
ini=ROOT/'build/native/termina-adventure-settings.ini';previous=ini.read_bytes() if ini.exists() else None
try:
 for name in ['ta_settings_load','ta_settings_save']:getattr(dll,name).argtypes=[c.c_void_p,c.POINTER(Context)]
 values=[0,1,0,1,1,1900,8,1,475,0,200,50,4,275,75,1];memory[:16]=values;dll.ta_settings_save(memory,c.byref(ctx));assert ctx.r[2]==1
 memory[:16]=[0]*16;dll.ta_settings_load(memory,c.byref(ctx));assert list(memory[:16])==values and ctx.r[2]==1
 ctx.r[5]=8;dll.ta_settings_save(memory,c.byref(ctx));assert ctx.r[2]==0
 ctx.r[5]=16;ctx.r[4]=0x80000001;dll.ta_settings_load(memory,c.byref(ctx));assert ctx.r[2]==0
finally:
 if previous is None:ini.unlink(missing_ok=True)
 else:ini.write_bytes(previous)
(ROOT/'docs/settings-0.1.22.json').write_text(json.dumps({'status':'passed','version':'0.1.22','checks':['held Z+Down in either order without press bits; targeting does not block; held chord does not repeat; pause blocks; navigation','Gamma 25-500 percent slider clamps','Gamma firing has exactly five named choices with clamped navigation and old values mapped to nearest choice','Big range and speed each have five named presets, nearest saved value migration and clamped navigation','independent Control hints toggle','audio toggle','close consumes B','sixteen settings persist through recomp CPU word ABI','invalid native pointers and counts rejected'],'actual_in_game_menu_verified':False},indent=2)+'\n')
print('PASS settings native persistence and ABI validation')
