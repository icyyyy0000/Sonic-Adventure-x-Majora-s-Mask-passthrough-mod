#include "characters/roster.h"
#include "modding.h"
#include "recompconfig.h"
#include "libu64/gfxprint.h"
RECOMP_IMPORT(".", u32 ta_settings_load(void* values,u32 count));
RECOMP_IMPORT(".", u32 ta_settings_save(void* values,u32 count));
u32 ta_menu_open,ta_settings[16]={1,1,1,1,1,1500,6,1,100,1,100,100,12,100,25,1};
static u32 initialized,row,chordHeld;
static const u32 grappleRanges[5]={600,1000,1500,2000,2400};
static const char* grappleRangeNames[5]={"Shortest","Short","Normal","Long","Longest"};
static u32 range_choice(u32 v){u32 best=0xffffffffu,c=0;for(u32 i=0;i<5;i++){u32 d=v>grappleRanges[i]?v-grappleRanges[i]:grappleRanges[i]-v;if(d<best){best=d;c=i;}}return c;}
static const u32 grappleSpeeds[5]={3,4,6,8,9};
static const char* grappleSpeedNames[5]={"Slowest","Slow","Normal","Fast","Fastest"};
static u32 speed_choice(u32 v){u32 best=0xffffffffu,c=0;for(u32 i=0;i<5;i++){u32 d=v>grappleSpeeds[i]?v-grappleSpeeds[i]:grappleSpeeds[i]-v;if(d<best){best=d;c=i;}}return c;}
static const u32 gammaFireTicks[5]={60,30,12,6,2};
static const char* gammaFireNames[5]={"Slowest","Slow","Normal","Fast","Fastest"};
static u32 gamma_fire_choice(u32 ticks){
    u32 choice=0,best=0xffffffffu;
    for(u32 i=0;i<5;i++){u32 d=ticks>gammaFireTicks[i] ? ticks-gammaFireTicks[i] : gammaFireTicks[i]-ticks;if(d<best){choice=i;best=d;}}
    return choice;
}
static const u32 menuOrder[16]={0,15,7,1,14,2,3,13,11,4,8,12,10,9,5,6};
static const char* labels[]={"Character HUD","Camera smoothing","Character sounds","Mute SADX music","Climb any surface","Big grapple range","Big grapple speed","Character models","Gamma hover speed","Big new mechanics","Amy hammer height","Character gravity","Gamma firing speed","Character speed","Camera follow speed","Control hints"};
void ta_menu_init(void){
    if(initialized)return;
    initialized=1;ta_settings[0]=recomp_get_config_u32("show_hud");
    ta_settings[7]=recomp_get_config_u32("character_models");
    ta_settings_load(ta_settings,16);
    for(u32 i=0;i<16;i++)if(i!=14 && i!=5 && i!=6 && i!=8 && i!=10 && i!=11 && i!=12 && i!=13)ta_settings[i]=!!ta_settings[i];
    if(ta_settings[5]<600 || ta_settings[5]>2400)ta_settings[5]=1500;
    ta_settings[5]=grappleRanges[range_choice(ta_settings[5])];
    if(ta_settings[6]<3 || ta_settings[6]>9)ta_settings[6]=6;
    ta_settings[6]=grappleSpeeds[speed_choice(ta_settings[6])];
    if(ta_settings[8]<25 || ta_settings[8]>500)ta_settings[8]=100;
    for(u32 i=10;i<14;i++)if(i!=12){
        if(ta_settings[i]<25 || ta_settings[i]>300)ta_settings[i]=100;
        ta_settings[i]=((ta_settings[i]+12)/25)*25;
    }
    if(ta_settings[12]<2 || ta_settings[12]>60)ta_settings[12]=12;
    ta_settings[12]=gammaFireTicks[gamma_fire_choice(ta_settings[12])];
    if(ta_settings[14]>100)ta_settings[14]=75;
    ta_settings[14]=((ta_settings[14]+12)/25)*25;
}
void ta_menu_update(Player* p,PlayState* play,Input* in){
    int held=(in->cur.button&BTN_DDOWN) && (in->cur.button&(BTN_Z|BTN_R));
    int chord=held && !chordHeld;chordHeld=held;
    // Targeting and transient host melee flags must not block the settings menu.
    int safe=p && p==GET_PLAYER(play) && play->pauseCtx.state==PAUSE_STATE_OFF &&
        play->csCtx.state==CS_STATE_IDLE && p->csAction==PLAYER_CSACTION_NONE &&
        play->transitionTrigger==TRANS_TRIGGER_OFF && play->msgCtx.msgMode==MSGMODE_NONE &&
        !(p->stateFlags1&PLAYER_STATE1_DEAD);
    if(chord && (ta_menu_open || safe)){
        ta_menu_open=!ta_menu_open;
        if(ta_menu_open){ta_big_reset();ta_state.attackTicks=0;}
        else ta_settings_save(ta_settings,16);
        return;
    }
    if(!ta_menu_open)return;
    if(in->press.button&(BTN_B|BTN_START)){ta_menu_open=0;ta_settings_save(ta_settings,16);in->cur.button=in->press.button=0;return;}
    if(in->press.button&BTN_DUP)row=(row+15)%16;
    if(in->press.button&BTN_DDOWN)row=(row+1)%16;
    int direction=(in->press.button&BTN_DRIGHT)?1:(in->press.button&BTN_DLEFT)?-1:0;
    if(!direction && !(in->press.button&BTN_A))return;
    u32 setting=menuOrder[row];
    if(setting==5){int c=range_choice(ta_settings[5]);c+=(direction?direction:1);if(c<0)c=0;if(c>4)c=4;ta_settings[5]=grappleRanges[c];return;}
    if(setting==6){int c=speed_choice(ta_settings[6]);c+=(direction?direction:1);if(c<0)c=0;if(c>4)c=4;ta_settings[6]=grappleSpeeds[c];return;}
    if(setting==12){
        int choice=gamma_fire_choice(ta_settings[12]);choice+=(direction?direction:1);
        if(choice<0)choice=0;if(choice>4)choice=4;ta_settings[12]=gammaFireTicks[choice];return;
    }
    if(setting==5 || setting==6 || setting==8 || setting==10 || setting==11 || setting==12 || setting==13 || setting==14){
        int value=ta_settings[setting],step=setting==5?100:(setting==6 || setting==12)?1:25;
        int minimum=setting==14?0:setting==5?600:setting==6?3:setting==12?2:25,maximum=setting==14?100:setting==5?2400:setting==6?9:setting==8?500:setting==12?60:300;
        value+=(direction?direction:1)*step;
        if(value<minimum)value=minimum;if(value>maximum)value=maximum;ta_settings[setting]=value;
    }else {ta_settings[setting]=!ta_settings[setting];if(setting==9)ta_big_reset();}
}
void ta_menu_draw(PlayState* play){
    GfxPrint printer;OPEN_DISPS(play->state.gfxCtx);
    gDPPipeSync(OVERLAY_DISP++);gDPSetCycleType(OVERLAY_DISP++,G_CYC_FILL);
    gDPSetFillColor(OVERLAY_DISP++,0x00010001);gDPFillRectangle(OVERLAY_DISP++,20,10,303,204);gDPPipeSync(OVERLAY_DISP++);
    GfxPrint_Init(&printer);GfxPrint_Open(&printer,OVERLAY_DISP);
    GfxPrint_SetColor(&printer,255,220,100,255);GfxPrint_SetPos(&printer,5,2);GfxPrint_Printf(&printer,"TERMINA ADVENTURE SETTINGS");
    for(u32 position=0;position<16;position++){
        u32 setting=menuOrder[position];
        GfxPrint_SetColor(&printer,position==row?255:180,position==row?230:180,position==row?100:180,255);
        GfxPrint_SetPos(&printer,4,4+position);GfxPrint_Printf(&printer,"%c %-19s ",position==row?'>':' ',labels[setting]);
        if(setting==14 && !ta_settings[setting])GfxPrint_Printf(&printer,"Off");
        else if(setting==14 && ta_settings[setting]==100)GfxPrint_Printf(&printer,"100%%");
        else if(setting==12)GfxPrint_Printf(&printer,"%s",gammaFireNames[gamma_fire_choice(ta_settings[setting])]);
        else if(setting==8 || setting==10 || setting==11 || setting==13 || setting==14)GfxPrint_Printf(&printer,"%u%%",ta_settings[setting]);
        else if(setting==5)GfxPrint_Printf(&printer,"%s",grappleRangeNames[range_choice(ta_settings[setting])]);
        else if(setting==6)GfxPrint_Printf(&printer,"%s",grappleSpeedNames[speed_choice(ta_settings[setting])]);
        else GfxPrint_Printf(&printer,"%s",ta_settings[setting]?"On":"Off");
    }
    u32 setting=menuOrder[row];
    if(setting==5 || setting==6 || setting==8 || (setting>=10 && setting!=15)){
        u32 lo=setting==14?0:setting==5?600:setting==6?3:setting==12?2:25,hi=setting==14?100:setting==5?2400:setting==6?9:setting==8?500:setting==12?60:300;
        u32 position=setting==6 ? speed_choice(ta_settings[setting])*14/4 : setting==12 ? gamma_fire_choice(ta_settings[setting])*14/4 : setting==5 ? range_choice(ta_settings[setting])*14/4 : (ta_settings[setting]-lo)*14/(hi-lo);
        GfxPrint_SetPos(&printer,9,21);GfxPrint_Printf(&printer,"[");
        for(u32 i=0;i<16;i++)GfxPrint_Printf(&printer,"%c",i==position?'O':'-');
        GfxPrint_Printf(&printer,"]");
    }
    GfxPrint_SetColor(&printer,235,235,235,255);GfxPrint_SetPos(&printer,3,23);GfxPrint_Printf(&printer,"D-pad: adjust  B/Start: save/close");
    OVERLAY_DISP=GfxPrint_Close(&printer);GfxPrint_Destroy(&printer);CLOSE_DISPS(play->state.gfxCtx);
}

// Suspend ordinary actor updates without changing Link's action/cutscene flags.
static struct {Actor* actor;s16 timer;s16 id;} menuActors[512];
static u32 menuActorCount;static PlayState* menuActorPlay;
RECOMP_HOOK("Actor_UpdateAll") void ta_menu_actors_enter(PlayState* play,ActorContext* ctx){
    menuActorCount=0;menuActorPlay=play;if(!ta_menu_open)return;
    for(u32 category=0;category<ACTORCAT_MAX;category++)for(Actor* actor=ctx->actorLists[category].first;actor;actor=actor->next){
        if(actor==&GET_PLAYER(play)->actor || !actor->update || menuActorCount>=512)continue;
        menuActors[menuActorCount].actor=actor;menuActors[menuActorCount].timer=actor->freezeTimer;menuActors[menuActorCount++].id=actor->id;
        actor->freezeTimer=2; // The engine decrements before deciding to update.
    }
}
RECOMP_HOOK_RETURN("Actor_UpdateAll") void ta_menu_actors_leave(void){
    if(!menuActorCount || !menuActorPlay)return;
    // Resolve through the current lists; a deleted actor is never dereferenced.
    for(u32 category=0;category<ACTORCAT_MAX;category++)for(Actor* actor=menuActorPlay->actorCtx.actorLists[category].first;actor;actor=actor->next)
        for(u32 i=0;i<menuActorCount;i++)if(actor==menuActors[i].actor && actor->id==menuActors[i].id){actor->freezeTimer=menuActors[i].timer;break;}
    menuActorCount=0;
}
