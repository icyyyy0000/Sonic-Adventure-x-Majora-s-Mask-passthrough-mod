#ifndef TA_CHARACTER_MODEL_H
#define TA_CHARACTER_MODEL_H
#include "global.h"
typedef struct {
    s16 parent;
    u16 flags;
    Vec3f pos;
    Vec3s ang;
    Vec3f scale;
    Gfx* displayList;
    s16 animIndex;
} TA_ModelNode;
typedef struct { s16 frame; Vec3f value; } TA_PosKey;
typedef struct { s16 frame; Vec3s value; } TA_RotKey;
typedef struct { s16 posCount, rotCount; TA_PosKey* positions; TA_RotKey* rotations; s16 scaleCount; TA_PosKey* scales; } TA_BoneTrack;
typedef struct { s16 frames; TA_BoneTrack* tracks; } TA_Animation;
typedef struct { s32 count; TA_ModelNode* nodes; TA_Animation* clips; } TA_CharacterModel;
typedef struct { s32 count; TA_ModelNode* nodes; TA_Animation clip; } TA_NativeAction;
extern TA_NativeAction ta_native_sonic[149],ta_native_tails[114],ta_native_knuckles[90];
extern TA_NativeAction ta_native_amy[80],ta_native_big[90],ta_native_gamma[78];
extern TA_CharacterModel ta_model_sonic, ta_model_tails, ta_model_knuckles;
extern TA_CharacterModel ta_model_amy, ta_model_big, ta_model_gamma;
#endif
