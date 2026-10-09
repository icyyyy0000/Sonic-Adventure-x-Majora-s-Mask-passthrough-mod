#include "characters/roster.h"
#include "modding.h"
#include "recompconfig.h"
#include "libu64/gfxprint.h"
void ta_menu_draw(PlayState*);
static PlayState* hudPlay;
static u32 lastCharacter=0xffffffffu,changedAt;
// Six-pixel glyphs use the stock font atlas (normal GfxPrint is eight pixels).
static void small_text(GfxPrint* p,int x,int y,const char* text){
    gDPSetCombineMode(p->dList++,G_CC_MODULATEIDECALA_PRIM,G_CC_MODULATEIDECALA_PRIM);
    for(;*text;text++,x+=6){
        u8 c=*text;if(c==' ')continue;
        u32 tile=c*2;u16 s=c&4,t=c>>3;
        gSPTextureRectangle(p->dList++,x*4,y*4,(x+6)*4,(y+6)*4,
                            tile,s<<6,t<<8,1365,1365);
    }
}
static const char* ability_hint(void){
    switch(ta_state.character){
    case TA_SONIC:return "A: jump/air home  Hold B: charge, release: dash";
    case TA_TAILS:return "A: jump, press again+hold: fly  B: tail spin";
    case TA_KNUCKLES:return "A: jump/hold: glide+climb  B: punch/drop";
    case TA_AMY:return "A: jump  B: hammer/hold: spin, running: vault";
    case TA_BIG:return ta_settings[9] ? "B: grapple  Air tap B: grapple, hold: stomp" : "A: jump  B: rod swing";
    case TA_GAMMA:return "A: jump/hold: hover  B: fire  Z: target";
    default:return "Link: normal Zelda controls";
    }
}
RECOMP_HOOK("Interface_Draw") void ta_hud_enter(PlayState* play) { hudPlay = play; }
RECOMP_HOOK_RETURN("Interface_Draw") void ta_hud_leave(void) {
    PlayState* play = hudPlay;
    if (!play || play->pauseCtx.state != PAUSE_STATE_OFF) return;
    if(ta_menu_open){ta_menu_draw(play);return;}
    if(!ta_settings[0] && !ta_settings[15])return;
    if (lastCharacter!=(u32)ta_state.character) {lastCharacter=ta_state.character;changedAt=play->gameplayFrames;}
    int name=ta_settings[0] && play->gameplayFrames-changedAt<=60;
    if(!name && !ta_settings[15])return;
    GfxPrint printer;
    OPEN_DISPS(play->state.gfxCtx);
    GfxPrint_Init(&printer);
    GfxPrint_Open(&printer, OVERLAY_DISP);
    if(name){
        GfxPrint_SetColor(&printer,235,235,235,210);GfxPrint_SetPos(&printer,2,24);
        GfxPrint_Printf(&printer,"%s",ta_roster[ta_state.character].name);
    }
    if(ta_settings[15]){
        GfxPrint_SetColor(&printer,210,210,210,145);
        small_text(&printer,8,214,"R+Left/Right: switch  R+Up: Link  Z/R+Down: menu");
        small_text(&printer,8,222,ability_hint());
        if(ta_state.character!=TA_LINK)small_text(&printer,8,230,"L: emote (standing still)");
    }
    OVERLAY_DISP = GfxPrint_Close(&printer);
    GfxPrint_Destroy(&printer);
    CLOSE_DISPS(play->state.gfxCtx);
}
