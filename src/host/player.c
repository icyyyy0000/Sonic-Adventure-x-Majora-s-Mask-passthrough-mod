#include "characters/roster.h"
#include "modding.h"
#include "recompconfig.h"
#include "recomputils.h"
TA_State ta_state = {0};
u32 ta_native_live;
u32 ta_native_owner, ta_native_visual;
static Vec3f heldPosition;
TA_GuestFrame ta_native_pose;
static Player* player;
static PlayState* context;
static Input savedInput, abilityInput;
static int routed, colliderReady, applied, initialized,menuConsumed;
static void mask_foreign_input(Player* p, Input* in) {
    if(ta_menu_open || menuConsumed){*in=(Input){0};return;}
    if (ta_state.character==TA_LINK) return;
    u16 mask=BTN_B|BTN_R|BTN_CUP|BTN_CDOWN|BTN_CLEFT|BTN_CRIGHT;
    mask|=BTN_L;
    if (!(p->stateFlags2&PLAYER_STATE2_CAN_ACCEPT_TALK_OFFER)) mask|=BTN_A;
    in->cur.button&=~mask;in->press.button&=~mask;in->rel.button&=~mask;
    if (ta_native_owner) {
        in->cur.stick_x=in->cur.stick_y=0;
        in->rel.stick_x=in->rel.stick_y=0;
    }
}
static ColliderCylinder attack;
static ColliderCylinderInit attackInit = {
    { COL_MATERIAL_HIT0, AT_ON | AT_TYPE_PLAYER, AC_NONE, OC1_NONE, OC2_NONE, COLSHAPE_CYLINDER },
    { ELEM_MATERIAL_UNK0, { DMG_GORON_PUNCH, 0, 2 }, { 0, 0, 0 },
      ATELEM_ON | ATELEM_SFX_NORMAL, ACELEM_NONE, OCELEM_NONE },
    { 24, 40, 0, { 0, 0, 0 } },
};
int ta_can_control(Player* p, PlayState* play) {
    return p && p == GET_PLAYER(play) && play->pauseCtx.state == PAUSE_STATE_OFF &&
           play->csCtx.state == CS_STATE_IDLE && p->csAction == PLAYER_CSACTION_NONE &&
           play->transitionTrigger == TRANS_TRIGGER_OFF &&
           play->msgCtx.msgMode == MSGMODE_NONE &&
           !(p->stateFlags1 & (PLAYER_STATE1_DEAD | PLAYER_STATE1_TALKING | PLAYER_STATE1_CARRYING_ACTOR |
                              PLAYER_STATE1_4 | PLAYER_STATE1_20000000)) &&
           !(p->stateFlags2 & (PLAYER_STATE2_USING_OCARINA | PLAYER_STATE2_80000000)) &&
           p->actor.freezeTimer == 0 && p->meleeWeaponState == 0;
}
void ta_launch(Player* p, f32 velocity) {
    p->actor.velocity.y = velocity;
    p->actor.bgCheckFlags &= ~(BGCHECKFLAG_GROUND | BGCHECKFLAG_GROUND_TOUCH);
    p->fallStartHeight = p->actor.world.pos.y;
}
void ta_begin_attack(TA_State* s, s16 ticks, s16 radius, s16 offset, u32 damageFlags) {
    s->attackTicks = ticks;
    s->attackRadius = radius;
    s->attackOffset = offset;
    s->damageFlags = damageFlags;
}
static void select_character(TA_Character next) {
    if(player && next!=TA_LINK){AudioSfx_StopByPos(&player->actor.projectedPos);player->actor.sfxId=0;}
    ta_big_reset();
    ta_emote_reset();
    ta_sonic_native_reset();
    ta_native_live = 0;
    ta_native_visual=0;
    ta_state = (TA_State){0};
    ta_state.character = next;
    recomp_printf("[Termina Adventure] Selected %s\n", ta_roster[next].name);
}
RECOMP_HOOK("Player_Init") void ta_player_init(Actor* actor, PlayState* play) {
    // Actor_Spawn links the category before initialization. Ignore player clones.
    if (actor != &GET_PLAYER(play)->actor) return;
    player = NULL; context = NULL; routed = 0;
    ta_menu_init();ta_menu_open=menuConsumed=0;
    if (!initialized) {
        u32 starting = recomp_get_config_u32("starting_character");
        select_character(starting < TA_CHARACTER_COUNT ? (TA_Character)starting : TA_LINK);
        initialized = 1;
    } else select_character(ta_state.character);
    Collider_InitCylinder(play, &attack);
    Collider_SetCylinder(play, &attack, actor, &attackInit);
    colliderReady = 1;
}
RECOMP_HOOK("Player_Destroy") void ta_player_destroy(Actor* actor, PlayState* play) {
    if (colliderReady && actor == attack.base.actor) {
        Collider_DestroyCylinder(play, &attack);
        colliderReady = 0; player = NULL; context = NULL; routed = 0;
        ta_sonic_play=NULL; ta_sonic_native_reset();
    }
}
RECOMP_HOOK("Player_Update") void ta_player_update_enter(Actor* actor, PlayState* play) {
    if (actor != &GET_PLAYER(play)->actor) { player = NULL; context = NULL; return; }
    player = (Player*)actor; context = play; ta_sonic_play=play; routed = 0; applied = 0;
    heldPosition=player->actor.world.pos;
    savedInput = abilityInput = *CONTROLLER1(&play->state);
    menuConsumed=ta_menu_open;ta_menu_update(player,play,&abilityInput);
    menuConsumed|=ta_menu_open;
    if(menuConsumed)ta_emote_reset();else ta_emote_update(player,play,&abilityInput);
    if(!menuConsumed && ta_state.character==TA_BIG)ta_big_capture_input(player,&abilityInput);
    if(menuConsumed){abilityInput=(Input){0};*CONTROLLER1(&play->state)=(Input){0};routed=1;return;}
    if (!ta_can_control(player, play)) {
        ta_state.burst = ta_state.charge = ta_state.attackTicks = ta_state.homingTicks = ta_state.climbing = 0;
        ta_state.homingTarget = NULL;
        if (ta_state.character!=TA_LINK) {mask_foreign_input(player,CONTROLLER1(&play->state));routed=1;}
        return;
    }
    Input* in = CONTROLLER1(&play->state);
    savedInput = abilityInput = *in;
    if (in->cur.button & BTN_R) {
        if (in->press.button & BTN_DUP) select_character(TA_LINK);
        else if (in->press.button & BTN_DRIGHT) select_character((ta_state.character + 1) % TA_CHARACTER_COUNT);
        else if (in->press.button & BTN_DLEFT) select_character((ta_state.character + TA_CHARACTER_COUNT - 1) % TA_CHARACTER_COUNT);
        in->cur.button &= ~(BTN_DUP | BTN_DDOWN | BTN_DLEFT | BTN_DRIGHT);
        in->press.button &= ~(BTN_DUP | BTN_DDOWN | BTN_DLEFT | BTN_DRIGHT);
        routed = 1;
    }
    if (ta_state.character == TA_LINK) return;
    // The guest owns A/B. Leave contextual A to Zelda for talking and doors.
    if (player->stateFlags2 & PLAYER_STATE2_CAN_ACCEPT_TALK_OFFER) {
        abilityInput.cur.button &= ~BTN_A;
        abilityInput.press.button &= ~BTN_A;
        in->cur.button &= ~BTN_B;
        in->press.button &= ~BTN_B;
    } else {
        in->cur.button &= ~(BTN_A | BTN_B);
        in->press.button &= ~(BTN_A | BTN_B);
    }
    routed = 1;
    mask_foreign_input(player,in);
    if ((ta_native_live && ta_native_pose.character == ta_state.character) || ta_native_owner) {
        in->cur.stick_x = in->cur.stick_y = 0;
        in->rel.stick_x = in->rel.stick_y = 0;
        player->speedXZ = player->actor.speed = 0;
    }
}
// Player_Update can substitute a scripted/override Input after our outer hook.
// Filter its final copy as well, so mask attacks cannot slip into the host FSM.
RECOMP_HOOK("Player_UpdateCommon") void ta_common_input(Player* p,PlayState* play,Input* in) {
    if (p==GET_PLAYER(play) && in) mask_foreign_input(p,in);
}
RECOMP_HOOK_RETURN("Player_Update") void ta_player_update_leave(void) {
    if (!player || !context) return;
    Player* p = player;
    PlayState* play = context;
    if (routed) *CONTROLLER1(&play->state) = savedInput;
    if(menuConsumed){p->actor.world.pos=heldPosition;p->actor.velocity=(Vec3f){0};p->speedXZ=p->actor.speed=0;return;}
    if (ta_state.character == TA_LINK || !ta_can_control(p, play)) return;
    TA_State* s = &ta_state;
    if(s->cooldown)s->cooldown--;
    if (ta_native_owner && !ta_native_live) {
        // A missing native reply is a wait, never permission to run the older
        // Zelda movement prototype or fall while collision is unavailable.
        p->actor.world.pos=heldPosition;p->actor.velocity=(Vec3f){0};
        p->speedXZ=p->actor.speed=0;s->attackTicks=0;
        return;
    }
    Vec3f homingHit;
    int hasHomingHit=0;
    if (ta_native_live && ta_native_pose.character == s->character) {
        p->actor.world.pos.x = -ta_native_pose.position[2] * 2.8f;
        p->actor.world.pos.y = ta_native_pose.position[1] * 2.8f;
        p->actor.world.pos.z = ta_native_pose.position[0] * 2.8f;
        p->actor.velocity.x = -ta_native_pose.velocity[2] * 2.8f;
        p->actor.velocity.y = ta_native_pose.velocity[1] * 2.8f;
        p->actor.velocity.z = ta_native_pose.velocity[0] * 2.8f;
        p->actor.shape.rot.y = -ta_native_pose.yaw;
        p->actor.world.rot.y = p->actor.shape.rot.y;
        p->speedXZ = p->actor.speed = 0;
        p->fallStartHeight = p->actor.world.pos.y;
        if (ta_native_pose.status & 1) p->actor.bgCheckFlags |= BGCHECKFLAG_GROUND;
        else p->actor.bgCheckFlags &= ~BGCHECKFLAG_GROUND;
        if (ta_native_pose.status & 0x400) ta_begin_attack(s, 1, 38, 25,
            ta_sonic_damage_flags(p,play));
        if (s->character==TA_SONIC && (hasHomingHit=ta_sonic_native_hit(p,play,&homingHit)))
            ta_begin_attack(s,1,40,0,ta_sonic_damage_flags(p,play));
    }
    if (ta_native_live && s->character == TA_GAMMA) ta_gamma_shoot(p, play, &abilityInput, s);
    if (ta_native_live && s->character == TA_BIG) ta_big_native_update(p,play,&abilityInput,s);
    if(ta_native_live && ((s->character==TA_KNUCKLES && (abilityInput.cur.button&BTN_B)) || (s->character==TA_BIG && !ta_settings[9] && (abilityInput.cur.button&BTN_B)) || (s->character==TA_TAILS && (ta_native_pose.action==0x14 || ta_native_pose.action==6)) ||
       (s->character==TA_AMY && ta_native_pose.action==0x14)))ta_begin_attack(s,1,s->character==TA_AMY ? 65 : 42,0,ta_sonic_damage_flags(p,play));
    Vec3f bigImpactPosition;
    int bigShock=s->character==TA_BIG && ta_big_shockwave(&bigImpactPosition);
    if(bigShock)ta_begin_attack(s,1,170,0,ta_sonic_damage_flags(p,play));
    if (s->attackTicks && colliderReady) {
        attack.dim.height=bigShock ? 100 : 40;attack.dim.yShift=bigShock ? -25 : 0;
        attack.dim.radius = s->attackRadius;
        attack.elem.atDmgInfo.dmgFlags = s->damageFlags;
        Collider_UpdateCylinder(&p->actor, &attack);
        attack.dim.pos.x += Math_SinS(p->actor.shape.rot.y) * s->attackOffset;
        attack.dim.pos.z += Math_CosS(p->actor.shape.rot.y) * s->attackOffset;
        if (hasHomingHit) {
            attack.dim.pos.x=homingHit.x;
            attack.dim.pos.y=homingHit.y-20;
            attack.dim.pos.z=homingHit.z;
        }
        if(bigShock){attack.dim.pos.x=bigImpactPosition.x;attack.dim.pos.y=bigImpactPosition.y;attack.dim.pos.z=bigImpactPosition.z;}
        CollisionCheck_SetAT(play, &play->colChkCtx, &attack.base);
        s->attackTicks--;
    }
}
RECOMP_HOOK("Actor_UpdateVelocityWithGravity") void ta_before_motion(Actor* actor) {
    if (!player || actor != &player->actor || applied || ta_state.character == TA_LINK ||
        !context || !ta_can_control(player, context)) return;
    applied = 1;
    Player* p = player;
    PlayState* play = context;
    TA_State* s = &ta_state;
    const TA_CharacterDef* def = &ta_roster[s->character];
    s->ticks++;

    if ((ta_native_live && ta_native_pose.character == s->character) || ta_native_owner) {
        p->speedXZ = p->actor.speed = 0;
        p->actor.velocity.x = p->actor.velocity.z = 0;
        p->actor.velocity.y = -p->actor.gravity;
        return;
    }
    s->jumpedThisFrame = 0;
    if (p->actor.bgCheckFlags & BGCHECKFLAG_GROUND) {
        s->flight = s->airJumpUsed = s->homingTicks = s->climbing = 0;
        if ((abilityInput.press.button & BTN_A) && !(p->stateFlags2 & PLAYER_STATE2_CAN_ACCEPT_TALK_OFFER)) {
            ta_launch(p, def->jumpSpeed);
            s->jumpedThisFrame = 1;
        }
    }
    if (ABS(abilityInput.cur.stick_x) + ABS(abilityInput.cur.stick_y) > 20 &&
        !(p->stateFlags1 & PLAYER_STATE1_8000000)) p->speedXZ = p->actor.speed = def->runSpeed;
    def->update(p, play, &abilityInput, s);
    if ((p->actor.bgCheckFlags & BGCHECKFLAG_CEILING) && p->actor.velocity.y > 0.0f) p->actor.velocity.y = 0.0f;
}
RECOMP_EXPORT void termina_adventure_select_character(u32 character) {
    if (character < TA_CHARACTER_COUNT && player && context && ta_can_control(player, context))
        select_character((TA_Character)character);
}
RECOMP_EXPORT u32 termina_adventure_get_character(void) { return ta_state.character; }
RECOMP_EXPORT u32 termina_adventure_can_control(void) { return !ta_menu_open && !menuConsumed && ta_can_control(player, context); }
RECOMP_EXPORT u32 termina_adventure_menu_open(void){return ta_menu_open || menuConsumed;}
RECOMP_EXPORT u32 termina_adventure_settings_flags(void){return TA_HOST_SETTINGS | (!ta_settings[2] ? TA_HOST_MUTE_CHARACTER : 0) | (!ta_settings[3] ? TA_HOST_ALLOW_MUSIC : 0) | (!ta_settings[4] ? TA_HOST_DISABLE_CLIMB : 0) | (!ta_settings[9] ? TA_HOST_BIG_ROD_ONLY : 0) | ((ta_settings[11]/25)<<TA_HOST_GRAVITY_SHIFT) | ((ta_settings[10]/25)<<TA_HOST_AMY_HEIGHT_SHIFT) | ((ta_settings[13]/25)<<TA_HOST_SPEED_SHIFT);}
RECOMP_EXPORT void termina_adventure_set_native_owner(u32 enabled) { ta_native_owner=enabled; }
RECOMP_EXPORT void termina_adventure_set_native_pose(TA_GuestFrame* pose) {
    ta_native_live = 0;
    if (!pose || pose->character != ta_state.character || !(pose->flags & TA_GUEST_NATIVE_ACTIVE)) return;
    for (s32 i = 0; i < 3; i++)
        if (!(pose->position[i] > -1000000.0f && pose->position[i] < 1000000.0f) ||
            !(pose->velocity[i] > -1000000.0f && pose->velocity[i] < 1000000.0f)) return;
    ta_native_pose = *pose;
    ta_native_live = 1;
    ta_native_visual=1;
}
RECOMP_EXPORT void termina_adventure_get_input(Input* output) {
    // Bridge hooks may run before our return hook restores the host's inputs.
    if (output && player && context) *output = abilityInput;
}

RECOMP_EXPORT u32 termina_adventure_gamma_speed(void){return ta_settings[8];}
