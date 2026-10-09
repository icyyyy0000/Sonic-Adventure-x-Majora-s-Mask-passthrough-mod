#include "characters/roster.h"
#include <math.h>
static u32 emoteCharacter,emoteStarted,emoteNow,emoteButtons;
static PlayState* emotePlay;
static s16 emoteScene;
static int emoteActive;
void ta_emote_reset(void){emoteActive=0;emotePlay=NULL;emoteButtons=0;}
int ta_emote_frame(void){return emoteActive ? (int)(emoteNow-emoteStarted)+1 : 0;}
void ta_emote_update(Player* p,PlayState* play,Input* in){
    u32 fresh=in->press.button|(in->cur.button&~emoteButtons);emoteButtons=in->cur.button;
    int valid=ta_state.character!=TA_LINK && ta_state.character!=TA_BIG && !ta_menu_open && ta_can_control(p,play);
    if(!valid){emoteActive=0;return;}
    int moving=ABS(in->cur.stick_x)>15 || ABS(in->cur.stick_y)>15;
    int grounded=(p->actor.bgCheckFlags&BGCHECKFLAG_GROUND)!=0;
    if(emoteActive && (emotePlay!=play || emoteScene!=play->sceneId || emoteCharacter!=(u32)ta_state.character ||
        play->gameplayFrames<emoteNow || play->gameplayFrames-emoteStarted>=40 || moving || !grounded ||
        (in->cur.button&(BTN_A|BTN_B)) || (fresh&BTN_L)))emoteActive=0;
    else if(!emoteActive && (fresh&BTN_L) && grounded && !moving && !(in->cur.button&(BTN_A|BTN_B))){
        f32 speed=ta_native_live ? fabsf(ta_native_pose.nativeSpeed[0])+fabsf(ta_native_pose.nativeSpeed[2]) : fabsf(p->actor.speed);
        if(speed<=.25f){emoteActive=1;emotePlay=play;emoteScene=play->sceneId;emoteCharacter=ta_state.character;emoteStarted=play->gameplayFrames;}
    }
    emoteNow=play->gameplayFrames;
}
