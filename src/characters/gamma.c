#include "characters/roster.h"
#include "overlays/actors/ovl_En_Arrow/z_en_arrow.h"
void func_8088ACE0(EnArrow*, PlayState*);
void ta_gamma_update(Player* p, PlayState* play, Input* in, TA_State* s) {
    if (!(p->actor.bgCheckFlags & BGCHECKFLAG_GROUND) && (in->cur.button & BTN_A) && s->flight < 60) {
        if (p->actor.velocity.y < -0.8f) p->actor.velocity.y = -0.8f;
        p->fallStartHeight = p->actor.world.pos.y;
        s->flight++;
    }
    ta_gamma_shoot(p, play, in, s);
}
void ta_gamma_shoot(Player* p, PlayState* play, Input* in, TA_State* s) {
    if ((in->press.button & BTN_B) && !s->cooldown) {
        Actor* t = p->focusActor;
        if (t && t->update && (t->category == ACTORCAT_ENEMY || t->category == ACTORCAT_BOSS))
            p->actor.shape.rot.y = p->actor.world.rot.y = Math_Atan2S(t->world.pos.x - p->actor.world.pos.x,
                                                                      t->world.pos.z - p->actor.world.pos.z);
        EnArrow* shot = (EnArrow*)Actor_Spawn(&play->actorCtx, play, ACTOR_EN_ARROW, p->actor.world.pos.x,
                    p->actor.world.pos.y + 24.0f, p->actor.world.pos.z,
                    0, p->actor.shape.rot.y, 0, 0);
        if (shot) {
            shot->actionFunc = func_8088ACE0;
            shot->unk_228 = shot->actor.world.pos;
            shot->unk_260 = 12;
            if (t && t->update && (t->category == ACTORCAT_ENEMY || t->category == ACTORCAT_BOSS)) {
                f32 dx = t->world.pos.x - shot->actor.world.pos.x;
                f32 dz = t->world.pos.z - shot->actor.world.pos.z;
                shot->actor.world.rot.x = Math_Atan2S(shot->actor.world.pos.y - t->world.pos.y - 15.0f,
                                                       sqrtf(dx * dx + dz * dz));
            }
            Actor_SetSpeeds(&shot->actor, 80.0f);
        }
        s->cooldown = ta_settings[12];
    }
}
