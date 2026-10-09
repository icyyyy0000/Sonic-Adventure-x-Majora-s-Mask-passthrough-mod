#include "characters/roster.h"
#include "modding.h"
#define ACTOR_AUDIO_FLAG_SFX_ALL 31
#define ACTOR_AUDIO_FLAG_SFX_ACTOR_POS_1 1
#define ACTOR_AUDIO_FLAG_SFX_ACTOR_POS_2 2
#define ACTOR_AUDIO_FLAG_SFX_CENTERED_1 4
#define ACTOR_AUDIO_FLAG_SFX_CENTERED_2 8
static int foreign_actor(Actor* actor){return ta_state.character!=TA_LINK && ta_sonic_play && actor==&GET_PLAYER(ta_sonic_play)->actor;}
RECOMP_PATCH void Player_PlaySfx(Player* player,u16 sfxId){
    if(foreign_actor(&player->actor))return;
    if(player->currentMask==PLAYER_MASK_GIANT)Audio_PlaySfx_AtPosWithPresetLowFreqAndHighReverb(&player->actor.projectedPos,sfxId);
    else AudioSfx_PlaySfx(sfxId,&player->actor.projectedPos,4,&gSfxDefaultFreqAndVolScale,&gSfxDefaultFreqAndVolScale,&gSfxDefaultReverb);
}
RECOMP_PATCH void Actor_PlaySfx(Actor* actor,u16 sfxId){if(!foreign_actor(actor))Audio_PlaySfx_AtPos(&actor->projectedPos,sfxId);}
RECOMP_PATCH void Actor_PlaySfx_Flagged2(Actor* actor,u16 sfxId){
    if(foreign_actor(actor)){actor->sfxId=0;return;}
    actor->sfxId=sfxId;actor->audioFlags&=~ACTOR_AUDIO_FLAG_SFX_ALL;actor->audioFlags|=ACTOR_AUDIO_FLAG_SFX_ACTOR_POS_2;
}
RECOMP_PATCH void Actor_PlaySfx_FlaggedCentered1(Actor* actor,u16 sfxId){
    if(foreign_actor(actor)){actor->sfxId=0;return;}
    actor->sfxId=sfxId;actor->audioFlags&=~ACTOR_AUDIO_FLAG_SFX_ALL;actor->audioFlags|=ACTOR_AUDIO_FLAG_SFX_CENTERED_1;
}
RECOMP_PATCH void Actor_PlaySfx_FlaggedCentered2(Actor* actor,u16 sfxId){
    if(foreign_actor(actor)){actor->sfxId=0;return;}
    actor->sfxId=sfxId;actor->audioFlags&=~ACTOR_AUDIO_FLAG_SFX_ALL;actor->audioFlags|=ACTOR_AUDIO_FLAG_SFX_CENTERED_2;
}
RECOMP_PATCH void Actor_PlaySfx_Flagged(Actor* actor,u16 sfxId){
    if(foreign_actor(actor)){actor->sfxId=0;return;}
    actor->sfxId=sfxId;actor->audioFlags&=~ACTOR_AUDIO_FLAG_SFX_ALL;actor->audioFlags|=ACTOR_AUDIO_FLAG_SFX_ACTOR_POS_1;
}

typedef enum AnimSfxType {
    /*  1 */ ANIMSFX_TYPE_GENERAL = 1,
    /*  2 */ ANIMSFX_TYPE_FLOOR,
    /*  3 */ ANIMSFX_TYPE_FLOOR_BY_AGE,
    /*  4 */ ANIMSFX_TYPE_VOICE,
    /*  5 */ ANIMSFX_TYPE_FLOOR_LAND, // does not use sfxId
    /*  6 */ ANIMSFX_TYPE_6,          // FLOOR_WALK_Something // does not use sfxId
    /*  7 */ ANIMSFX_TYPE_FLOOR_JUMP, // does not use sfxId
    /*  8 */ ANIMSFX_TYPE_8,          // FLOOR_WALK_Something2 // does not use sfxId
    /*  9 */ ANIMSFX_TYPE_9,          // Uses NA_SE_PL_WALK_LADDER // does not use sfxId, unused
    /* 10 */ ANIMSFX_TYPE_SURFACE
} AnimSfxType;

#define ANIMSFX_SHIFT_TYPE(type) ((type) << 11)

#define ANIMSFX_GET_TYPE(data) ((data)&0x7800)
#define ANIMSFX_GET_FRAME(data) ((data)&0x7FF)
typedef struct {u16 sfxId;s16 flags;} AnimSfxEntry;
void Player_AnimSfx_PlayFloor(Player*,u16);
void Player_AnimSfx_PlayFloorByAge(Player*,u16);
void Player_AnimSfx_PlayVoice(Player*,u16);
void Player_AnimSfx_PlayFloorLand(Player*);
void Player_AnimSfx_PlayFloorWalk(Player*,f32);
void Player_AnimSfx_PlayFloorJump(Player*);
RECOMP_PATCH void Player_PlayAnimSfx(Player* this, AnimSfxEntry* entry) {
    if(foreign_actor(&this->actor))return;
    s32 cond;

    do {
        s32 data = ABS_ALT(entry->flags);
        s32 type = ANIMSFX_GET_TYPE(data);

        if (PlayerAnimation_OnFrame(&this->skelAnime, fabsf(ANIMSFX_GET_FRAME(data)))) {
            if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_GENERAL)) {
                Player_PlaySfx(this, entry->sfxId);
            } else if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_FLOOR)) {
                Player_AnimSfx_PlayFloor(this, entry->sfxId);
            } else if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_FLOOR_BY_AGE)) {
                Player_AnimSfx_PlayFloorByAge(this, entry->sfxId);
            } else if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_VOICE)) {
                Player_AnimSfx_PlayVoice(this, entry->sfxId);
            } else if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_FLOOR_LAND)) {
                Player_AnimSfx_PlayFloorLand(this);
            } else if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_6)) {
                Player_AnimSfx_PlayFloorWalk(this, 6.0f);
            } else if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_FLOOR_JUMP)) {
                Player_AnimSfx_PlayFloorJump(this);
            } else if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_8)) {
                Player_AnimSfx_PlayFloorWalk(this, 0.0f);
            } else if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_9)) {
                // Audio_PlaySfx_AtPosForMetalEffectsWithSyncedFreqAndVolume
                Audio_PlaySfx_AtPosForMetalEffectsWithSyncedFreqAndVolume(
                    &this->actor.projectedPos, this->ageProperties->surfaceSfxIdOffset + NA_SE_PL_WALK_LADDER, 0.0f);
            } else if (type == ANIMSFX_SHIFT_TYPE(ANIMSFX_TYPE_SURFACE)) {
                Player_PlaySfx(this, entry->sfxId + this->ageProperties->surfaceSfxIdOffset);
            }
        }

        cond = entry->flags >= 0;
        entry++;
    } while (cond);
}

