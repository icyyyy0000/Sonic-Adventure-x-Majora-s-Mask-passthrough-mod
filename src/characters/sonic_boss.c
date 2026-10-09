#include "characters/roster.h"
// Official ovl_Boss_Hakugin layout: bodyCollider is at 0x484. Access just the
// public collision struct, avoiding a dependency on unavailable object assets.
#ifdef MIPS
typedef char TA_GohtLayoutCheck[(sizeof(Actor)==0x144 && sizeof(ColliderJntSph)==0x20) ? 1 : -1];
#endif
int ta_sonic_target_point(Player* p,Actor* target,Vec3f* point,f32* radius) {
    *point=target->focus.pos;*radius=10;
    if (point->y<target->world.pos.y+10) point->y=target->world.pos.y+15;
    if (target->id!=ACTOR_BOSS_HAKUGIN) return 1;
    ColliderJntSph* col=(ColliderJntSph*)((u8*)target+0x484);
    if (col->base.actor!=target || col->base.shape!=COLSHAPE_JNTSPH || col->count!=19 || !col->elements) return 0;
    f32 best=1e9f;
    int found=0;
    for (s32 i=0;i<col->count;i++) {
        ColliderJntSphElement* elem=&col->elements[i];
        if (!(elem->base.acElemFlags&ACELEM_ON) || elem->dim.worldSphere.radius<=0) continue;
        Vec3s c=elem->dim.worldSphere.center;
        f32 dx=p->actor.world.pos.x-c.x,dy=p->actor.world.pos.y+15-c.y,dz=p->actor.world.pos.z-c.z;
        f32 distance=sqrtf(dx*dx+dy*dy+dz*dz);
        f32 r=elem->dim.worldSphere.radius;
        f32 inward=distance>1 ? MIN(r*.6f,distance)/distance : 0;
        Vec3f candidate={c.x+dx*inward,c.y+dy*inward,c.z+dz*inward};
        f32 score=MAX(0,distance-r)+MAX(0,candidate.y-p->actor.world.pos.y)*2;
        if (score>=best) continue;
        *point=candidate;
        *radius=CLAMP(r/2.8f*.25f,5,15);
        best=score;found=1;
    }
    return found;
}
u32 ta_sonic_damage_flags(Player* p,PlayState* play) {
    // Goron-spike damage is the native physical spinning hit bosses such as
    // running Goht accept. Keep ordinary sword compatibility for other enemies.
    for (Actor* boss=play->actorCtx.actorLists[ACTORCAT_BOSS].first;boss;boss=boss->next) {
        if (!boss->update || !boss->colChkInfo.health || !(boss->flags&ACTOR_FLAG_ATTENTION_ENABLED)) continue;
        f32 dx=boss->world.pos.x-p->actor.world.pos.x,dy=boss->world.pos.y-p->actor.world.pos.y,dz=boss->world.pos.z-p->actor.world.pos.z;
        if (dx*dx+dy*dy+dz*dz<600.0f*600.0f) return DMG_GORON_SPIKES;
    }
    return DMG_SWORD;
}
