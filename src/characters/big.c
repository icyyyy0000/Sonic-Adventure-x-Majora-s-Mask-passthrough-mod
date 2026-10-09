#include "characters/roster.h"
#include "modding.h"
#include <math.h>
static u32 bigCommand, bigMode, bigImpact;
static s16 bigTicks,bigCooldown;
static s16 bigPending,bigCastBuffer;
static s16 bigHoldTicks,bigStompBuffer;
static u32 bigInputPrevious;
void ta_big_capture_input(Player* p,Input* in){
    if(bigCastBuffer)--bigCastBuffer;
    if(bigStompBuffer)--bigStompBuffer;
    u32 fresh=in->press.button|(in->cur.button&~bigInputPrevious);bigInputPrevious=in->cur.button;
    if(!ta_settings[9]){bigPending=bigHoldTicks=bigCastBuffer=bigStompBuffer=0;return;}
    if(fresh&BTN_A){bigPending=bigHoldTicks=bigCastBuffer=bigStompBuffer=0;return;}
    if(fresh&BTN_B){
        // A new B press cancels an active pull/drop without queuing another.
        if(bigMode==1 || bigMode==2){bigPending=bigCastBuffer=bigStompBuffer=0;return;}
        if(p->actor.bgCheckFlags&BGCHECKFLAG_GROUND){bigCastBuffer=8;bigPending=0;}
        else {bigPending=1;bigHoldTicks=0;}
    }
    if(bigPending){
        if(!(in->cur.button&BTN_B) || (p->actor.bgCheckFlags&BGCHECKFLAG_GROUND)){
            bigCastBuffer=8;bigPending=0;bigHoldTicks=0;
        }else if(!(fresh&BTN_B) && ++bigHoldTicks>=5){
            bigStompBuffer=8;bigPending=0;bigHoldTicks=0;
        }
    }
}
static s16 bigShockTicks;
static Vec3f bigShockPosition;
int ta_big_emote_frame(void){return bigMode==3 ? bigTicks+1 : 0;}
int ta_big_shockwave(Vec3f* pos){if(!bigShockTicks)return 0;--bigShockTicks;*pos=bigShockPosition;return 1;}
static Vec3f bigAnchor,bigGoal;
static Vec3f anchorNormal,anchorActorPosition;
static s32 anchorBgId=BGCHECK_SCENE;
static DynaPolyActor* anchorActor;
void ta_big_reset(void) {bigMode=0;bigTicks=bigCooldown=bigPending=0;bigImpact=0;bigShockTicks=0;bigCastBuffer=bigHoldTicks=bigStompBuffer=0;bigInputPrevious=0;}
int ta_big_line(Vec3f* endpoint) {if(bigMode!=1)return 0;*endpoint=bigAnchor;return 1;}
RECOMP_EXPORT void termina_adventure_get_big_command(TA_HostFrame* frame) {
    if (!frame || !bigMode) return;
    frame->flags|=bigMode==1 ? TA_HOST_BIG_GRAPPLE : bigMode==2 ? TA_HOST_BIG_SLAM : TA_HOST_BIG_EMOTE;
    frame->targetId=bigCommand;
    frame->targetRadius=ta_settings[6];
    frame->targetPosition[0]=bigGoal.z/2.8f;
    frame->targetPosition[1]=bigGoal.y/2.8f;
    frame->targetPosition[2]=-bigGoal.x/2.8f;
}
void ta_big_native_update(Player* p,PlayState* play,Input* in,TA_State* s) {
    if (!ta_settings[9] && bigMode!=3){bigMode=0;bigPending=0;bigShockTicks=0;bigCastBuffer=0;}
    if (bigCooldown)bigCooldown--;
    if (bigMode==2 && ta_native_pose.hitTargetId==bigCommand && (ta_native_pose.renderFlags&TA_RENDER_BIG_IMPACT) && ta_native_pose.hitSequence!=bigImpact) {
        bigImpact=ta_native_pose.hitSequence;
        bigShockTicks=8;bigShockPosition=p->actor.world.pos;
        Actor_SpawnFloorDustRing(play,&p->actor,&p->actor.world.pos,120,16,4,220,20,false);
        Rumble_Request(0,180,12,20);
    }
    if(bigCastBuffer && bigMode==3){bigMode=0;bigCooldown=0;}
    if (bigMode) {
        bigTicks++;
        if (bigMode==1) {
            if (anchorActor) {
                DynaPolyActor* actor=DynaPoly_GetActor(&play->colCtx,anchorBgId);
                if (actor!=anchorActor) {bigMode=0;bigCooldown=6;return;}
                Vec3f delta={actor->actor.world.pos.x-anchorActorPosition.x,actor->actor.world.pos.y-anchorActorPosition.y,actor->actor.world.pos.z-anchorActorPosition.z};
                if (fabsf(delta.x)+fabsf(delta.y)+fabsf(delta.z)>200) {bigMode=0;return;}
                bigAnchor.x+=delta.x;bigAnchor.y+=delta.y;bigAnchor.z+=delta.z;
                bigGoal.x+=delta.x;bigGoal.y+=delta.y;bigGoal.z+=delta.z;anchorActorPosition=actor->actor.world.pos;
            }
            Vec3f a={bigAnchor.x+anchorNormal.x*6,bigAnchor.y+anchorNormal.y*6,bigAnchor.z+anchorNormal.z*6};
            Vec3f b={bigAnchor.x-anchorNormal.x*6,bigAnchor.y-anchorNormal.y*6,bigAnchor.z-anchorNormal.z*6},hit;
            CollisionPoly* poly=NULL;s32 bgId;
            if (!BgCheck_EntityLineTest2(&play->colCtx,&a,&b,&hit,&poly,true,true,true,false,&bgId,&p->actor)) {bigMode=0;bigCooldown=6;return;}
        }
        if ((bigMode==3 && (bigTicks>=40 || in->cur.stick_x>15 || in->cur.stick_x< -15 || in->cur.stick_y>15 || in->cur.stick_y< -15 || (in->press.button&BTN_L))) ||
            (in->press.button&(BTN_A|BTN_B)) || bigTicks>240 ||
            (ta_native_pose.hitTargetId==bigCommand && !(ta_native_pose.renderFlags&(TA_RENDER_BIG_GRAPPLE|TA_RENDER_BIG_SLAM|TA_RENDER_BIG_EMOTE)))) {
            bigMode=0;bigCooldown=6;bigCastBuffer=bigPending=bigStompBuffer=0;
        }
        return;
    }
    if ((in->press.button&BTN_L) && (p->actor.bgCheckFlags&BGCHECKFLAG_GROUND)) {bigMode=3;bigTicks=0;bigPending=0;++bigCommand;return;}
    if(!ta_settings[9])return;
    if(bigStompBuffer){
        bigStompBuffer=0;
        if(!(p->actor.bgCheckFlags&BGCHECKFLAG_GROUND)){bigMode=2;bigTicks=0;bigCooldown=0;++bigCommand;return;}
        bigCastBuffer=8;
    }
    if(!bigCastBuffer)return;
    // Search a small character-facing cone at torso heights, never camera aim.
    // Thick characters and uneven terrain must not depend on one low ray.
    f32 range=ta_settings[5],best=1e20f;Vec3f start,bestStart;
    CollisionPoly* poly=NULL;s32 bgId=BGCHECK_SCENE;
    const s16 angles[5]={0,-1638,1638,-3277,3277};const f32 heights[4]={48,24,68,96};
    for(s32 h=0;h<4;h++)for(s32 a=0;a<5;a++){
        Vec3f from=p->actor.world.pos;from.y+=heights[h];
        s16 yaw=p->actor.shape.rot.y+angles[a];
        Vec3f end={from.x+Math_SinS(yaw)*range,from.y,from.z+Math_CosS(yaw)*range},hit;
        CollisionPoly* candidate=NULL;s32 candidateBg;
        if(!BgCheck_EntityLineTest2(&play->colCtx,&from,&end,&hit,&candidate,true,true,true,false,&candidateBg,&p->actor) || !candidate)continue;
        f32 dx=hit.x-from.x,dy=hit.y-from.y,dz=hit.z-from.z;
        f32 distance=sqrtf(dx*dx+dy*dy+dz*dz);
        if(distance<30 || distance>range+1)continue;
        f32 score=distance+(a?80:0)+h*20;
        if(score>=best)continue;
        best=score;bigAnchor=hit;bestStart=from;poly=candidate;bgId=candidateBg;
    }
    if(!poly)return;
    start=bestStart;
    anchorBgId=bgId;anchorActor=bgId!=BGCHECK_SCENE ? DynaPoly_GetActor(&play->colCtx,bgId) : NULL;
    if (anchorActor)anchorActorPosition=anchorActor->actor.world.pos;
    Vec3f normal={poly->normal.x/32767.0f,poly->normal.y/32767.0f,poly->normal.z/32767.0f};
    f32 facing=normal.x*(start.x-bigAnchor.x)+normal.y*(start.y-bigAnchor.y)+normal.z*(start.z-bigAnchor.z);
    if (facing<0) {normal.x=-normal.x;normal.y=-normal.y;normal.z=-normal.z;}
    anchorNormal=normal;
    bigGoal=(Vec3f){bigAnchor.x+normal.x*24,bigAnchor.y+normal.y*24-20,bigAnchor.z+normal.z*24};
    bigCastBuffer=0;bigCooldown=0;bigMode=1;bigTicks=0;++bigCommand;
}
void ta_big_update(Player* p, PlayState* play, Input* in, TA_State* s) {
    if ((p->actor.bgCheckFlags & BGCHECKFLAG_WATER) && (in->cur.button & BTN_A)) {
        p->actor.velocity.y = 2.0f;
        p->fallStartHeight = p->actor.world.pos.y;
    }
    if ((in->press.button & BTN_B) && !s->cooldown) {
        ta_begin_attack(s, 5, 24, 65, DMG_DEKU_STICK);
        s->cooldown = 15;
    }
}
