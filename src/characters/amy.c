#include "characters/roster.h"
void ta_amy_update(Player* p, PlayState* play, Input* in, TA_State* s) {
    if ((in->press.button & BTN_B) && !s->cooldown) {
        // Original Amy vaults by swinging while running on the ground.
        // Native mode uses the actual Amy task; this is the disconnected fallback.
        if ((p->actor.bgCheckFlags & BGCHECKFLAG_GROUND) && p->actor.speed > 4.0f) ta_launch(p, 16.0f);
        ta_begin_attack(s, 5, 38, 32, DMG_GORON_POUND);
        s->cooldown = 12;
    }
}
