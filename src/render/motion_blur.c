#include "characters/roster.h"
#include "modding.h"
#include "regs.h"

static int blurSuppressed;
static s16 savedBlur,savedPriority;
RECOMP_HOOK("Play_DrawMotionBlur") void ta_motion_blur_enter(PlayState* play){
    blurSuppressed=0;
    if(!play || ta_state.character==TA_LINK || !ta_native_owner || !ta_native_visual ||
       !ta_can_control(GET_PLAYER(play),play))return;
    // Let the original draw reset its framebuffer history without blending old
    // guest frames. Preserve the game's requests for Link and scripted effects.
    savedBlur=R_MOTION_BLUR_ENABLED;savedPriority=R_MOTION_BLUR_PRIORITY_ENABLED;
    R_MOTION_BLUR_ENABLED=R_MOTION_BLUR_PRIORITY_ENABLED=0;blurSuppressed=1;
}
RECOMP_HOOK_RETURN("Play_DrawMotionBlur") void ta_motion_blur_leave(void){
    if(!blurSuppressed)return;
    R_MOTION_BLUR_ENABLED=savedBlur;R_MOTION_BLUR_PRIORITY_ENABLED=savedPriority;
    blurSuppressed=0;
}
