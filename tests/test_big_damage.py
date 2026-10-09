"""Exercise the production impact collider registration, not just the impact command."""
from pathlib import Path
import subprocess,os,re,json
R=Path(__file__).resolve().parents[1];W=R.parents[1]/'work'
s=(R/'src/host/player.c').read_text();s=s[s.index('    Vec3f bigImpactPosition;'):s.index('\nRECOMP_HOOK("Actor_UpdateVelocityWithGravity")')];s=s[:s.rfind('\n}')]
preamble=r'''
#include <assert.h>
#include <stdio.h>
typedef struct {float x,y,z;} Vec3f;
typedef struct {struct {Vec3f pos;} world;struct {struct {short y;} rot;} shape;} Actor;
typedef struct {Actor actor;} Player;
typedef struct {int colChkCtx;} PlayState;
typedef struct {int character,attackTicks,attackRadius,attackOffset;unsigned damageFlags;} TA_State;
typedef struct {struct {int radius,height,yShift;struct {short x,y,z;} pos;} dim;struct {struct {unsigned dmgFlags;} atDmgInfo;} elem;int base;} ColliderCylinder;
#define TA_BIG 5
#define DMG_SWORD (1u<<9)
static ColliderCylinder attack;static int colliderReady=1,hasHomingHit=0;static Vec3f homingHit;
static int shockTicks=8,registrations;static Vec3f origin={100,20,200};
static int ta_big_shockwave(Vec3f* pos){if(!shockTicks)return 0;--shockTicks;*pos=origin;return 1;}
static unsigned ta_sonic_damage_flags(Player* p,PlayState* play){return DMG_SWORD;}
static void ta_begin_attack(TA_State* s,int ticks,int radius,int offset,unsigned flags){s->attackTicks=ticks;s->attackRadius=radius;s->attackOffset=offset;s->damageFlags=flags;}
static float Math_SinS(short y){return 0;}
static float Math_CosS(short y){return 1;}
static void Collider_UpdateCylinder(Actor* a,ColliderCylinder* c){c->dim.pos.x=a->world.pos.x;c->dim.pos.y=a->world.pos.y;c->dim.pos.z=a->world.pos.z;}
static void CollisionCheck_SetAT(PlayState* play,int* ctx,int* base){registrations++;assert(attack.elem.atDmgInfo.dmgFlags==DMG_SWORD);assert(attack.dim.radius==170 && attack.dim.height==100 && attack.dim.yShift==-25);assert(attack.dim.pos.x==100 && attack.dim.pos.y==20 && attack.dim.pos.z==200);}
static void tick(Player* p,PlayState* play,TA_State* s){
'''
checks=r'''
}
int main(){Player p={0};PlayState play={0};TA_State s={.character=TA_BIG};p.actor.world.pos=(Vec3f){999,999,999};
 for(int i=0;i<8;i++)tick(&p,&play,&s);assert(registrations==8);tick(&p,&play,&s);assert(registrations==8);
 puts("PASS Big impact registers eight wide damaging collision frames anchored at landing, not subsequent player position");}
'''
f=W/'big_damage_unit.c';f.write_text(preamble+s+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(W/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(W/'zig-local-cache');exe=R/'build/native/big_damage_unit.exe'
subprocess.run([str(W/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc',str(f),'-o',str(exe)],env=env,check=True);subprocess.run([str(exe)],check=True)
# The damage flag follows the existing working physical attack compatibility path.
checked=[]
for path in [R/'mm-decomp/src/overlays/actors/ovl_En_Bb/z_en_bb.c',R/'mm-decomp/src/overlays/actors/ovl_En_Dekubaba/z_en_dekubaba.c']:
 match=re.search(r'/\* Sword\s*\*/ DMG_ENTRY\((\d+),',path.read_text());assert match and int(match[1])>0;checked.append(path.parent.name)
(R/'docs/big-damage-0.1.21.json').write_text(json.dumps({'status':'passed','checks':['production AT cylinder registration for eight frames','fixed impact anchor while player moves','170 radius,100 height,-25 vertical shift','existing sword/boss-compatible damage path'],'positive_damage_tables_checked':checked,'actual_enemy_fight_verified':False},indent=2)+'\n')
