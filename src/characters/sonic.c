#include "characters/roster.h"
#include "modding.h"
PlayState* ta_sonic_play;
static Actor* lastNativeHit;
static int visible_target(Player* p, PlayState* play, Actor* t) {
    Vec3f start = p->actor.world.pos, end, hit;
    f32 radius;
    if (!ta_sonic_target_point(p,t,&end,&radius)) return 0;
    CollisionPoly* poly;
    s32 bgId;
    start.y += 16.0f;
    if (end.y < t->world.pos.y + 10.0f) end.y = t->world.pos.y + 15.0f;
    return !BgCheck_EntityLineTest1(&play->colCtx, &start, &end, &hit, &poly, true, true, true, true, &bgId);
}
static Actor* find_target(Player* p, PlayState* play, Actor* previous) {
    Actor* best = NULL;
    f32 score = 350.0f * 350.0f;
    // Validate pointers by list membership before dereferencing; targets can despawn.
    for (s32 category = 0; category < ACTORCAT_MAX; category++) {
        if (category != ACTORCAT_ENEMY && category != ACTORCAT_BOSS) continue;
        for (Actor* t = play->actorCtx.actorLists[category].first; t; t = t->next) {
            if (!previous && ta_native_live && t==lastNativeHit && !(p->actor.bgCheckFlags&BGCHECKFLAG_GROUND)) continue;
            if (!t->update || !t->colChkInfo.health || !(t->flags & ACTOR_FLAG_ATTENTION_ENABLED)) continue;
            Vec3f point;f32 radius;
            if (!ta_sonic_target_point(p,t,&point,&radius)) continue;
            f32 dx = point.x - p->actor.world.pos.x;
            f32 dy = point.y - p->actor.world.pos.y;
            f32 dz = point.z - p->actor.world.pos.z;
            f32 distance = dx * dx + dy * dy + dz * dz;
            if (distance > 350.0f * 350.0f) continue;
            f32 ahead = dx * Math_SinS(p->actor.shape.rot.y) + dz * Math_CosS(p->actor.shape.rot.y);
            if (!previous && t != p->focusActor && ahead < -20.0f) continue;
            if (previous && t != previous) continue;
            if (distance < score && visible_target(p, play, t)) { best = t; score = distance; }
        }
    }
    return best;
}
void ta_sonic_update(Player* p, PlayState* play, Input* in, TA_State* s) {
    int ground = p->actor.bgCheckFlags & BGCHECKFLAG_GROUND;
    if (ground && (in->cur.button & BTN_B)) {
        if (s->charge < 30) s->charge++;
        s->burst = 0;
        p->speedXZ = p->actor.speed = 0.0f;
        ta_begin_attack(s, 2, 22, 0, DMG_GORON_SPIKES);
    } else if (s->charge) { s->burst = 10 + s->charge / 2; s->charge = 0; }
    if (s->burst) {
        p->actor.speed = p->speedXZ = 10.0f + 8.0f * (s->burst > 10 ? 1.0f : s->burst / 10.0f);
        ta_begin_attack(s, 2, 22, 12, DMG_GORON_SPIKES);
        s->burst--;
    }
    if (!ground && !s->jumpedThisFrame && (in->press.button & (BTN_A | BTN_B)) && !s->airJumpUsed) {
        s->homingTarget = find_target(p, play, NULL);
        s->homingTicks = 12; s->burst = 0; s->airJumpUsed = 1;
    }
    if (s->homingTicks) {
        Actor* t = s->homingTarget ? find_target(p, play, s->homingTarget) : NULL;
        if (t) {
            f32 dx = t->world.pos.x - p->actor.world.pos.x;
            f32 dz = t->world.pos.z - p->actor.world.pos.z;
            f32 dy = t->world.pos.y + 15.0f - p->actor.world.pos.y;
            p->actor.world.rot.y = p->actor.shape.rot.y = Math_Atan2S(dx, dz);
            p->actor.speed = p->speedXZ = 17.0f;
            p->actor.velocity.y = CLAMP(dy * 0.20f, -10.0f, 10.0f) - p->actor.gravity;
            if (dx * dx + dz * dz + dy * dy < 35.0f * 35.0f) {
                ta_launch(p, 7.0f); p->actor.speed = p->speedXZ = 2.0f; s->homingTicks = 1;
            }
        } else {
            s->homingTarget = NULL;
            p->actor.speed = p->speedXZ = 15.0f;
            p->actor.velocity.y = -p->actor.gravity;
        }
        ta_begin_attack(s, 2, 24, 12, DMG_GORON_SPIKES);
        s->homingTicks--;
    }
}

static Actor* nativeTarget;
static u32 targetSerial;
static u32 nativeTargetId;
static u32 consumedHit;
// A reply can arrive after the observer has selected the next enemy. Retain
// identities across that boundary, and validate membership before dereferencing.
static struct { Actor* actor; u32 id; } targetHistory[32];
RECOMP_EXPORT void termina_adventure_get_sonic_target(TA_HostFrame* packet) {
    if (!packet || ta_state.character!=TA_SONIC) return;
    if (!ta_sonic_play) return;
    Player* p=GET_PLAYER(ta_sonic_play);
    if ( !ta_can_control(p,ta_sonic_play)) return;
    Actor* target=find_target(p,ta_sonic_play,
        ta_native_live && ta_native_pose.action==14 ? nativeTarget : NULL);
    if (target!=nativeTarget) {
        nativeTarget=target;nativeTargetId=++targetSerial;
        if (!nativeTargetId) nativeTargetId=++targetSerial;
        targetHistory[nativeTargetId%32].actor=target;
        targetHistory[nativeTargetId%32].id=nativeTargetId;
    }
    if (!target) return;
    packet->flags|=TA_HOST_HOMING_TARGET;
    packet->targetId=nativeTargetId;
    Vec3f point;f32 radius;
    if (!ta_sonic_target_point(p,target,&point,&radius)) {packet->flags&=~TA_HOST_HOMING_TARGET;return;}
    packet->targetPosition[0]=point.z/2.8f;
    packet->targetPosition[1]=point.y/2.8f;
    packet->targetPosition[2]=-point.x/2.8f;
    packet->targetRadius=radius;
}
int ta_sonic_native_hit(Player* p,PlayState* play,Vec3f* hit) {
    if (ta_native_pose.hitSequence==consumedHit) return 0;
    consumedHit=ta_native_pose.hitSequence;
    u32 id=ta_native_pose.hitTargetId;
    Actor* previous=targetHistory[id%32].id==id ? targetHistory[id%32].actor : NULL;
    Actor* valid=previous ? find_target(p,play,previous) : NULL;
    if (!valid) return 0;
    lastNativeHit=valid;
    f32 radius;
    return ta_sonic_target_point(p,valid,hit,&radius);
}
void ta_sonic_native_reset(void) {
    nativeTarget=NULL;nativeTargetId=0;consumedHit=ta_native_pose.hitSequence;
    lastNativeHit=NULL;
    for (int i=0;i<32;i++) {targetHistory[i].actor=NULL;targetHistory[i].id=0;}
}
