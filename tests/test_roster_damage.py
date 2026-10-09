"""Exercise the production punch/spin/rod collision trigger and damage selection."""
from pathlib import Path
import os,subprocess,json
R=Path(__file__).resolve().parents[1];W=R.parents[1]/'work';s=(R/'src/host/player.c').read_text();s=s[s.index('    if(ta_native_live && (('):s.index('    Vec3f bigImpactPosition;')]
preamble=r'''
#include <assert.h>
#include <stdio.h>
#define TA_KNUCKLES 3
#define TA_TAILS 2
#define TA_AMY 4
#define TA_BIG 5
#define BTN_B 0x4000
#define DMG_SWORD 0x400
#define DMG_GORON_SPIKES 0x800
static struct {int action;} ta_native_pose;
static struct {struct {unsigned button;} cur;} abilityInput;
static unsigned ta_settings[12]={1,1,1,1,1,1500,6,1,100,1,100,100};
static int ta_native_live=1,boss,calls,radius;static unsigned damage;
typedef struct {int character;} TA_State;typedef struct {int unused;} Player,PlayState;
static unsigned ta_sonic_damage_flags(Player* p,PlayState* play){return boss?DMG_GORON_SPIKES:DMG_SWORD;}
static void ta_begin_attack(TA_State* s,int ticks,int r,int offset,unsigned flags){assert(ticks==1);calls++;radius=r;damage=flags;}
static void tick(Player* p,PlayState* play,TA_State* s){
'''
checks=r'''
}
int main(){Player p={0};PlayState play={0};TA_State s={0};
 for(int b=0;b<2;b++){boss=b;for(int ch=2;ch<=5;ch++){
  calls=0;s.character=ch;ta_native_pose.action=20;abilityInput.cur.button=BTN_B;ta_settings[9]=0;tick(&p,&play,&s);
  assert(calls==1 && damage==(b?DMG_GORON_SPIKES:DMG_SWORD));assert(radius==(ch==4?65:42));
 }}
 s.character=3;calls=0;abilityInput.cur.button=0;tick(&p,&play,&s);assert(!calls);
 s.character=2;calls=0;ta_native_pose.action=1;tick(&p,&play,&s);assert(!calls);
 s.character=4;calls=0;ta_native_pose.action=1;tick(&p,&play,&s);assert(!calls);
 puts("PASS production Knuckles punches, Tails/Amy spins and Big rod swing register compatible enemy/boss damage; idle produces no attacks");}
'''
f=W/'roster_damage_unit.c';f.write_text(preamble+s+checks);env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(W/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(W/'zig-local-cache');exe=R/'build/native/roster_damage_unit.exe';subprocess.run([str(W/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc',str(f),'-o',str(exe)],env=env,check=True);subprocess.run([str(exe)],check=True)
(R/'docs/roster-damage-0.1.21.json').write_text(json.dumps({'status':'passed','checks':['Knuckles B punch, Tails action20 spin, Amy action20 spin and Big rod register attacks','ordinary enemies use established sword profile','bosses use established spike profile','idle suppresses punch/spin attacks'],'actual_enemy_fights_verified':False},indent=2)+'\n')
