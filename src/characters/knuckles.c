#include "characters/roster.h"
static int wall_probe(Player* p, PlayState* play, s16 yaw, CollisionPoly** poly) {
    Vec3f start = p->actor.world.pos, end, hit;
    s32 bgId;
    start.y += 20.0f; end = start;
    end.x -= Math_SinS(yaw) * 40.0f;
    end.z -= Math_CosS(yaw) * 40.0f;
    return BgCheck_EntityLineTest1(&play->colCtx, &start, &end, &hit, poly, true, false, false, false, &bgId) &&
           *poly && ABS((*poly)->normal.y) < 16384;
}
void ta_knuckles_update(Player* p, PlayState* play, Input* in, TA_State* s) {
    int wasClimbing = s->climbing;
    int ground = p->actor.bgCheckFlags & BGCHECKFLAG_GROUND;
    if (!ground && !s->climbing && (in->cur.button & BTN_A) &&
        (p->actor.bgCheckFlags & BGCHECKFLAG_WALL) && p->actor.wallPoly &&
        ABS(p->actor.wallPoly->normal.y) < 16384) {
        s->climbing = 1; s->climbYaw = p->actor.wallYaw;
    }
    if (s->climbing) {
        CollisionPoly* poly = NULL;
        if (ground || !wall_probe(p, play, s->climbYaw, &poly)) s->climbing = 0;
        else if (wasClimbing && (in->press.button & BTN_A)) {
            s->climbing = 0;
            p->actor.world.rot.y = p->actor.shape.rot.y = s->climbYaw;
            p->actor.speed = p->speedXZ = 6.0f; ta_launch(p, 9.0f);
        } else {
            s->climbYaw = Math_Atan2S(poly->normal.x, poly->normal.z);
            f32 sideways = in->cur.stick_x / 80.0f, vertical = in->cur.stick_y / 80.0f;
            if (ABS(in->cur.stick_x) < 15) sideways = 0.0f;
            if (ABS(in->cur.stick_y) < 15) vertical = 0.0f;
            p->actor.shape.rot.y = s->climbYaw + 0x8000;
            p->actor.world.rot.y = s->climbYaw + (sideways >= 0.0f ? -0x4000 : 0x4000);
            p->actor.speed = p->speedXZ = ABS(sideways) * 2.0f;
            p->actor.velocity.y = vertical * 2.5f - p->actor.gravity;
            p->actor.world.pos.x -= Math_SinS(s->climbYaw) * 0.5f;
            p->actor.world.pos.z -= Math_CosS(s->climbYaw) * 0.5f;
            if ((p->actor.bgCheckFlags & BGCHECKFLAG_CEILING) && vertical > 0.0f)
                p->actor.velocity.y = -p->actor.gravity;
            p->fallStartHeight = p->actor.world.pos.y;
        }
    } else if (!ground && (in->cur.button & BTN_A) && p->actor.velocity.y < -1.3f) {
        p->actor.velocity.y = -1.3f - p->actor.gravity;
        p->speedXZ = p->actor.speed = 9.0f; p->fallStartHeight = p->actor.world.pos.y;
    }
    if ((in->press.button & BTN_B) && !s->cooldown) {
        ta_begin_attack(s, 4, 24, 30, DMG_GORON_PUNCH); s->cooldown = 8;
    }
}
