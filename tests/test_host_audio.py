"""Production host sound dispatch: selected character, real player and world actors."""
import os,subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parents[1]/'work'
s='\n'.join(v for v in (ROOT/'src/host/audio.c').read_text().splitlines() if not v.startswith('#include'))
preamble=r'''
#include <assert.h>
#include <stdio.h>
typedef unsigned short u16;typedef short s16;typedef int s32;typedef float f32;
#include <math.h>
#define ABS_ALT(x) ((x)<0?-(x):(x))
#define NA_SE_PL_WALK_LADDER 1234
typedef struct {int projectedPos;unsigned sfxId,audioFlags;} Actor;
typedef struct {int surfaceSfxIdOffset;} Age;
typedef struct {Actor actor;int currentMask,skelAnime;Age* ageProperties;} Player;
typedef struct {Player* player;} PlayState;
#define GET_PLAYER(p) ((p)->player)
#define TA_LINK 0
#define PLAYER_MASK_GIANT 1
#define RECOMP_PATCH
static struct {int character;} ta_state;static PlayState* ta_sonic_play;
static int calls,giantCalls,lastTone,gSfxDefaultFreqAndVolScale,gSfxDefaultReverb;
static void Audio_PlaySfx_AtPosWithPresetLowFreqAndHighReverb(int* p,unsigned tone){giantCalls++;lastTone=tone;}
static void AudioSfx_PlaySfx(unsigned tone,int* p,int channel,int* freq,int* vol,int* reverb){calls++;lastTone=tone;}
static void Audio_PlaySfx_AtPos(int* p,unsigned tone){calls++;lastTone=tone;}
static int animationCalls,walkCalls;
static int PlayerAnimation_OnFrame(int* anim,float frame){animationCalls++;return 1;}
static void Player_AnimSfx_PlayFloor(Player* p,u16 id){calls++;}
static void Player_AnimSfx_PlayFloorByAge(Player* p,u16 id){calls++;}
static void Player_AnimSfx_PlayVoice(Player* p,u16 id){calls++;}
static void Player_AnimSfx_PlayFloorLand(Player* p){calls++;}
static void Player_AnimSfx_PlayFloorWalk(Player* p,float value){walkCalls++;}
static void Player_AnimSfx_PlayFloorJump(Player* p){calls++;}
static void Audio_PlaySfx_AtPosForMetalEffectsWithSyncedFreqAndVolume(int* pos,u16 id,float f){walkCalls++;}
'''
checks=r'''
int main(){Player p={0},clone={0};Actor enemy={0};PlayState play={&p};ta_sonic_play=&play;
 for(int character=1;character<=6;character++){
  ta_state.character=character;Player_PlaySfx(&p,123);Actor_PlaySfx(&p.actor,124);assert(!calls && !giantCalls);
  p.actor.audioFlags=0x40;Actor_PlaySfx_Flagged(&p.actor,125);assert(!p.actor.sfxId && p.actor.audioFlags==0x40);
 }
 ta_state.character=0;Player_PlaySfx(&p,123);assert(calls==1 && lastTone==123);
 p.currentMask=1;Player_PlaySfx(&p,126);assert(giantCalls==1 && lastTone==126);
 ta_state.character=1;Actor_PlaySfx(&enemy,127);assert(calls==2 && lastTone==127);
 Player_PlaySfx(&clone,128);assert(calls==3);Actor_PlaySfx_Flagged(&enemy,129);assert(enemy.sfxId==129 && enemy.audioFlags==1);
 AnimSfxEntry entry={0,-((6<<11)|1)};ta_state.character=1;Player_PlayAnimSfx(&p,&entry);assert(!animationCalls && !walkCalls);ta_state.character=0;Player_PlayAnimSfx(&p,&entry);assert(animationCalls==1 && walkCalls==1);
 ta_sonic_play=0;Player_PlaySfx(&p,130);assert(giantCalls==2);
 puts("PASS host Link/body sounds suppressed only for selected foreign player; Link, giant pitch, clones and world actors preserved");}
'''
p=WORK/'host_audio_unit.c';p.write_text(preamble+s+checks)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(WORK/'zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(WORK/'zig-local-cache')
exe=ROOT/'build/native/host_audio_unit.exe';subprocess.run([str(WORK/'tools/zig-windows-x86_64-0.13.0/zig.exe'),'cc',str(p),'-o',str(exe)],env=env,check=True);subprocess.run([str(exe)],check=True)
(ROOT/'docs/host-audio-0.1.21.json').write_text(json.dumps({'status':'passed','checks':['all six foreign characters suppress Link positional/body sounds','Link regular and giant sounds preserved','animation events including direct floor-walk sounds filtered for foreign player','other actors and player clones unchanged','no gameplay context preserves original audio'],'actual_audio_listening_verified':False},indent=2)+'\n')
