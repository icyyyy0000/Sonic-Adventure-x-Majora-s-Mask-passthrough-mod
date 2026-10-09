#include "characters/roster.h"
void ta_tails_update(Player* p, PlayState* play, Input* in, TA_State* s) {
    if (!(p->actor.bgCheckFlags & BGCHECKFLAG_GROUND) && !s->jumpedThisFrame &&
        (in->press.button & BTN_A)) s->airJumpUsed = 1;
    if (s->airJumpUsed && !(p->actor.bgCheckFlags & BGCHECKFLAG_GROUND) && (in->cur.button & BTN_A) && s->flight < 80) {
        if (!(p->actor.bgCheckFlags & BGCHECKFLAG_CEILING)) p->actor.velocity.y = 2.5f;
        s->flight++;
        p->fallStartHeight = p->actor.world.pos.y;
    }
    if ((in->press.button & BTN_B) && !s->cooldown) {
        ta_begin_attack(s, 5, 30, 0, DMG_GORON_PUNCH);
        s->cooldown = 8;
    }
}
