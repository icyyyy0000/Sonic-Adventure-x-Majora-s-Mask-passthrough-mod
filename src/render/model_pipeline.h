#ifndef TA_MODEL_PIPELINE_H
#define TA_MODEL_PIPELINE_H
#include "ultra64.h"
static inline Gfx* ta_model_pipeline(Gfx* next) {
    gDPPipeSync(next++);
    // Zelda's setup enables fog: RT64 then replaces vertex alpha with fog alpha.
    // Imported texture alpha must reach the alpha test without that substitution.
    gSPClearGeometryMode(next++, G_LIGHTING | G_FOG | G_CULL_BACK | G_CULL_FRONT |
                                  G_TEXTURE_GEN | G_TEXTURE_GEN_LINEAR);
    gSPSetGeometryMode(next++, G_SHADE | G_SHADING_SMOOTH | G_ZBUFFER);
    gDPSetCycleType(next++, G_CYC_1CYCLE);
    gDPSetRenderMode(next++, G_RM_AA_ZB_OPA_SURF, G_RM_AA_ZB_OPA_SURF2);
    gSPTexture(next++, 0xFFFF, 0xFFFF, 0, G_TX_RENDERTILE, G_ON);
    gDPSetCombineMode(next++, G_CC_MODULATERGBA, G_CC_MODULATERGBA);
    gDPSetTextureLUT(next++, G_TT_NONE);
    gDPSetBlendColor(next++, 0, 0, 0, 128);
    gDPSetAlphaCompare(next++, G_AC_THRESHOLD);
    return next;
}
#endif
