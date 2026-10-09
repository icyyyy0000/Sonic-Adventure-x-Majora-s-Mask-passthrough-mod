#include "global.h"
#include "modding.h"
#include "recomputils.h"
#include "recompconfig.h"
#include "bridge_protocol.h"
RECOMP_IMPORT("termina_adventure", u32 termina_adventure_get_character(void));
RECOMP_IMPORT("termina_adventure", void termina_adventure_get_input(Input* output));
RECOMP_IMPORT("termina_adventure", u32 termina_adventure_can_control(void));
RECOMP_IMPORT("termina_adventure", void termina_adventure_set_native_pose(TA_GuestFrame* pose));
RECOMP_IMPORT("termina_adventure", void termina_adventure_set_native_owner(u32 enabled));
RECOMP_IMPORT(".", u32 ta_bridge_publish(void* frame, u32 words));
RECOMP_IMPORT(".", u32 ta_bridge_poll(void* frame, u32 words));
RECOMP_IMPORT(".", void ta_bridge_close(void));
RECOMP_IMPORT(".", u32 ta_bridge_next_epoch(void));
RECOMP_IMPORT("termina_adventure", void termina_adventure_get_sonic_target(TA_HostFrame* packet));
RECOMP_IMPORT("termina_adventure", void termina_adventure_get_big_command(TA_HostFrame* packet));
RECOMP_IMPORT("termina_adventure", u32 termina_adventure_settings_flags(void));
RECOMP_IMPORT("termina_adventure", u32 termina_adventure_menu_open(void));
RECOMP_IMPORT("termina_adventure", u32 termina_adventure_gamma_speed(void));
static TA_GuestFrame cachedGuest;
static u32 haveGuest;
static Player* currentPlayer;
static PlayState* currentPlay;
static u32 frameNumber, epoch, lastFlags = 0xffffffffu;
void ta_export_world(Player*, PlayState*, u32, u32);
RECOMP_HOOK("Player_Init") void ta_observer_init(Actor* actor, PlayState* play) {
    if (actor == &GET_PLAYER(play)->actor) {epoch=ta_bridge_next_epoch();haveGuest=0;}
}
RECOMP_HOOK("Player_Update") void ta_observer_enter(Actor* actor, PlayState* play) {
    currentPlayer = actor == &GET_PLAYER(play)->actor ? (Player*)actor : NULL;
    currentPlay = play;
    TA_GuestFrame guest;
    if (ta_bridge_poll(&guest, sizeof(guest) / 4)) {cachedGuest=guest;haveGuest=1;}
    else guest=cachedGuest;
    u32 character = termina_adventure_get_character();
    termina_adventure_set_native_owner(character!=0 && recomp_get_config_u32("native_physics"));
    if (currentPlayer && recomp_get_config_u32("native_physics") && haveGuest &&
        guest.character == character && guest.scene == (u32)play->sceneId && guest.epoch == epoch &&
        (guest.flags & 15) == 15 && guest.hostFrame <= frameNumber && frameNumber - guest.hostFrame < 4)
        termina_adventure_set_native_pose(&guest);
    else termina_adventure_set_native_pose(NULL);
}
RECOMP_HOOK_RETURN("Player_Update") void ta_observer_leave(void) {
    if (!currentPlayer) return;
    Player* p = currentPlayer;
    PlayState* play = currentPlay;
    Input saved = *CONTROLLER1(&play->state);
    termina_adventure_get_input(&saved);
    Input* in = &saved;
    TA_HostFrame frame = {0};
    frame.frame = ++frameNumber;
    frame.scene = play->sceneId;
    frame.epoch = epoch;
    frame.character = termina_adventure_get_character();
    frame.buttons = in->cur.button;
    frame.stickX = in->cur.stick_x;
    frame.stickY = in->cur.stick_y;
    // Same handedness, both Y-up: SADX +X faces Zelda +Z.
    frame.position[0] = p->actor.world.pos.z / 2.8f;
    frame.position[1] = p->actor.world.pos.y / 2.8f;
    frame.position[2] = -p->actor.world.pos.x / 2.8f;
    frame.velocity[0] = p->actor.velocity.z / 2.8f;
    frame.velocity[1] = p->actor.velocity.y / 2.8f;
    frame.velocity[2] = -p->actor.velocity.x / 2.8f;
    frame.floorHeight = p->actor.floorHeight / 2.8f;
    if (p->actor.floorPoly) {
        frame.floorNormal[0] = p->actor.floorPoly->normal.z / 32767.0f;
        frame.floorNormal[1] = p->actor.floorPoly->normal.y / 32767.0f;
        frame.floorNormal[2] = -p->actor.floorPoly->normal.x / 32767.0f;
    }
    frame.grounded = (p->actor.bgCheckFlags & BGCHECKFLAG_GROUND) != 0;
    frame.yaw = (u16)-p->actor.shape.rot.y;
    frame.cameraYaw = (u16)-Camera_GetInputDirYaw(GET_ACTIVE_CAM(play));
    if (frame.character && termina_adventure_can_control()) frame.flags = TA_HOST_GAMEPLAY;
    if (frame.character && recomp_get_config_u32("native_physics")) frame.flags |= TA_HOST_NATIVE_PHYSICS;
    if (play->pauseCtx.state != PAUSE_STATE_OFF) frame.flags |= TA_HOST_PAUSED;
    frame.flags|=termina_adventure_settings_flags();
    if(frame.character==6)frame.targetRadius=termina_adventure_gamma_speed();
    if(termina_adventure_menu_open()){frame.flags|=TA_HOST_PAUSED;frame.buttons=frame.stickX=frame.stickY=0;}
    if (frame.character==1 && (frame.flags & TA_HOST_GAMEPLAY)) termina_adventure_get_sonic_target(&frame);
    if (frame.character==5 && (frame.flags & TA_HOST_GAMEPLAY)) termina_adventure_get_big_command(&frame);
    ta_bridge_publish(&frame, sizeof(frame) / 4);
    if (frame.flags & TA_HOST_GAMEPLAY) ta_export_world(p, play, epoch, frameNumber);
    TA_GuestFrame guest;
    u32 flags = ta_bridge_poll(&guest, sizeof(guest) / 4) ? guest.flags : 0;
    if (flags != lastFlags) {
        recomp_printf("[Termina Bridge] SADX bridge status = %u (1=player, 2=character matches, 4=world converted, 8=original physics)\n", flags);
        lastFlags = flags;
    }
    // Ownership is applied on the next player update, after epoch and scene checks.
}
RECOMP_HOOK("Player_Destroy") void ta_observer_destroy(Actor* actor, PlayState* play) {
    if (actor == &GET_PLAYER(play)->actor) { ta_bridge_close(); currentPlayer = NULL; }
}
