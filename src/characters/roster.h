#ifndef TA_ROSTER_H
#define TA_ROSTER_H
#include "global.h"
#include "bridge_protocol.h"
typedef enum { TA_LINK, TA_SONIC, TA_TAILS, TA_KNUCKLES, TA_AMY, TA_BIG, TA_GAMMA, TA_CHARACTER_COUNT } TA_Character;
typedef struct {
    TA_Character character;
    s16 charge, flight, burst, cooldown, attackTicks, airJumpUsed;
    s16 homingTicks, climbing;
    s16 jumpedThisFrame, climbYaw;
    Actor* homingTarget;
    u32 ticks;
    s16 attackRadius, attackOffset;
    u32 damageFlags;
} TA_State;
typedef void (*TA_AbilityUpdate)(Player*, PlayState*, Input*, TA_State*);
typedef struct {
    const char* name;
    const char* ability;
    s16 sadxId;
    f32 runSpeed, jumpSpeed, modelScale;
    TA_AbilityUpdate update;
} TA_CharacterDef;
extern TA_State ta_state;
extern u32 ta_native_live;
extern u32 ta_native_owner, ta_native_visual;
extern TA_GuestFrame ta_native_pose;
extern const TA_CharacterDef ta_roster[TA_CHARACTER_COUNT];
extern PlayState* ta_sonic_play;
int ta_sonic_native_hit(Player*,PlayState*,Vec3f*);
void ta_sonic_native_reset(void);
int ta_sonic_target_point(Player*,Actor*,Vec3f*,f32*);
u32 ta_sonic_damage_flags(Player*,PlayState*);
void ta_sonic_update(Player*, PlayState*, Input*, TA_State*);
void ta_tails_update(Player*, PlayState*, Input*, TA_State*);
void ta_knuckles_update(Player*, PlayState*, Input*, TA_State*);
void ta_amy_update(Player*, PlayState*, Input*, TA_State*);
void ta_big_update(Player*, PlayState*, Input*, TA_State*);
void ta_big_native_update(Player*,PlayState*,Input*,TA_State*);
void ta_big_reset(void);
void ta_big_capture_input(Player*,Input*);
int ta_big_line(Vec3f*);
int ta_big_emote_frame(void);
void ta_emote_reset(void);
void ta_emote_update(Player*,PlayState*,Input*);
int ta_emote_frame(void);
int ta_big_shockwave(Vec3f*);
void ta_menu_init(void);
void ta_menu_update(Player*,PlayState*,Input*);
extern u32 ta_menu_open,ta_settings[16];
void ta_gamma_shoot(Player*, PlayState*, Input*, TA_State*);
void ta_gamma_update(Player*, PlayState*, Input*, TA_State*);
int ta_can_control(Player*, PlayState*);
void ta_begin_attack(TA_State*, s16, s16, s16, u32);
void ta_launch(Player*, f32);
#endif
