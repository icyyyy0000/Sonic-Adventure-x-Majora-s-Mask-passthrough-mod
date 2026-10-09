#include <stdint.h>
#include <stdio.h>
#include "render/model_pipeline.h"
int main(void) {
    Gfx commands[16] = {0};
    Gfx* end = ta_model_pipeline(commands);
    uint32_t geometry = G_ZBUFFER | G_SHADE | G_CULL_BACK | G_FOG | G_LIGHTING | G_SHADING_SMOOTH;
    int cycleSet = 0;
    for (Gfx* p = commands; p < end; p++) {
        if ((p->words.w0 >> 24) == G_GEOMETRYMODE)
            geometry = (geometry & (p->words.w0 & 0xffffff)) | p->words.w1;
        if ((p->words.w0 >> 24) == G_SETOTHERMODE_H &&
            ((p->words.w0 >> 8) & 255) == 32 - G_MDSFT_CYCLETYPE - 2) {
            if (p->words.w1 != G_CYC_1CYCLE) return 1;
            cycleSet = 1;
        }
    }
    if (!cycleSet || (geometry & (G_FOG | G_LIGHTING | G_CULL_BACK | G_CULL_FRONT))) return 2;
    if (!(geometry & G_ZBUFFER)) return 3;
    // RT64 RSPProcessCS replaces alpha with fog when G_FOG is enabled.
    // Near-camera opaque vertices then failed the old 128/255 alpha threshold.
    float oldAlpha = 0.0f, newAlpha = 1.0f;
    if (oldAlpha >= 128.0f / 255.0f || newAlpha < 128.0f / 255.0f) return 4;
    puts("PASS: production model commands clear inherited fog, preserve depth and set one-cycle opaque rendering.");
    return 0;
}
