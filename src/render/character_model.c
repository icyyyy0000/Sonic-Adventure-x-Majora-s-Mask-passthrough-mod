#include "render/character_model.h"
#include "characters/roster.h"
#include "modding.h"
#include "recompconfig.h"
#include "rt64_extended_gbi.h"
#include "recomputils.h"
#include "render/model_pipeline.h"
#include "render/emote_pose.h"
static Player* drawingPlayer;
static PlayState* drawingPlay;
static u32 originalHide;
static int drawCharacter;
u32 ta_model_draw_frames;
static MtxF nodeMatrices[128];
static TA_ModelNode* renderRoots[TA_CHARACTER_COUNT];
static u32 renderGenerations[TA_CHARACTER_COUNT];
static s16 sonicTiltX,sonicTiltZ;
static u32 sonicTiltFrame,sonicTiltEpoch,sonicTiltScene;
static int sonicTiltValid;
static void sample_track(TA_BoneTrack* t, f32 frame, Vec3f* pos, Vec3s* rot) {
    if (t->posCount) {
        s32 a = 0;
        while (a + 1 < t->posCount && t->positions[a + 1].frame <= frame) a++;
        s32 b = a + 1 < t->posCount ? a + 1 : a;
        f32 weight = a == b ? 0.0f : (frame - t->positions[a].frame) / (t->positions[b].frame - t->positions[a].frame);
        Vec3f* av = &t->positions[a].value;
        Vec3f* bv = &t->positions[b].value;
        pos->x = av->x + (bv->x - av->x) * weight;
        pos->y = av->y + (bv->y - av->y) * weight;
        pos->z = av->z + (bv->z - av->z) * weight;
    }
    if (t->rotCount) {
        s32 a = 0;
        while (a + 1 < t->rotCount && t->rotations[a + 1].frame <= frame) a++;
        s32 b = a + 1 < t->rotCount ? a + 1 : a;
        f32 weight = a == b ? 0.0f : (frame - t->rotations[a].frame) / (t->rotations[b].frame - t->rotations[a].frame);
        Vec3s* av = &t->rotations[a].value;
        Vec3s* bv = &t->rotations[b].value;
        rot->x = av->x + (s16)(bv->x - av->x) * weight;
        rot->y = av->y + (s16)(bv->y - av->y) * weight;
        rot->z = av->z + (s16)(bv->z - av->z) * weight;
    }
}
static void sample_scale(TA_BoneTrack* t, f32 frame, Vec3f* scale) {
    TA_BoneTrack scaleTrack = {t->scaleCount, 0, t->scales, NULL, 0, NULL};
    Vec3s unused = {0};
    if (t->scales && t->scaleCount) sample_track(&scaleTrack, frame, scale, &unused);
}
RECOMP_HOOK("Player_Draw") void ta_draw_enter(Actor* actor, PlayState* play) {
    drawingPlayer = (Player*)actor;
    drawingPlay = play;
    drawCharacter = actor == &GET_PLAYER(play)->actor && ta_state.character != TA_LINK &&
                    ta_settings[7] != 0;
    originalHide = drawingPlayer->stateFlags2 & PLAYER_STATE2_20000000;
    if (originalHide) drawCharacter = 0;
    if (drawCharacter) drawingPlayer->stateFlags2 |= PLAYER_STATE2_20000000;
}
RECOMP_HOOK_RETURN("Player_Draw") void ta_draw_leave(void) {
    if (!drawingPlayer || !drawCharacter) return;
    Player* p = drawingPlayer;
    PlayState* play = drawingPlay;
    p->stateFlags2 = (p->stateFlags2 & ~PLAYER_STATE2_20000000) | originalHide;
    int useNative=ta_native_live || (ta_native_owner && ta_native_visual && ta_native_pose.character==ta_state.character);
    TA_CharacterModel* models[] = { NULL, &ta_model_sonic, &ta_model_tails, &ta_model_knuckles,
                                  &ta_model_amy, &ta_model_big, &ta_model_gamma };
    TA_CharacterModel* model = models[ta_state.character];
    if (!model || model->count > 128) return;
    s32 clipIndex = (p->actor.bgCheckFlags & BGCHECKFLAG_GROUND) ? (p->actor.speed > 0.5f ? 1 : 0) : 2;
    if (ta_state.attackTicks || ta_state.charge || ta_state.climbing ||
        (ta_state.flight && (CONTROLLER1(&play->state)->cur.button & BTN_A))) clipIndex = 3;
    TA_Animation* anim = &model->clips[clipIndex];
    if (!anim->tracks) anim = &model->clips[0];
    f32 frame = (f32)(ta_state.ticks * 3 % (u32)(anim->frames > 0 ? anim->frames : 1));
    TA_ModelNode* nodes = model->nodes;
    s32 nodeCount = model->count;
    TA_NativeAction* nativeActions[] = {NULL,ta_native_sonic,ta_native_tails,ta_native_knuckles,ta_native_amy,ta_native_big,ta_native_gamma};
    u32 actionCounts[] = {0,149,114,90,80,90,78};
    TA_NativeAction* previousAction = NULL;
    f32 blend = 1.0f;
    if (useNative && ta_native_pose.character == ta_state.character && ta_native_pose.actionIndex < actionCounts[ta_state.character]) {
        TA_NativeAction* action = &nativeActions[ta_state.character][ta_native_pose.actionIndex];
        if (action->count > 0 && action->count <= 128 && action->nodes && action->clip.tracks) {
            nodes = action->nodes;nodeCount = action->count;anim = &action->clip;
            frame = ta_native_pose.animationFrame;
            if (!(frame >= 0.0f && frame < 100000.0f)) frame = 0;
            while (frame >= anim->frames && anim->frames > 0) frame -= anim->frames;
            if (ta_native_pose.previousActionIndex < actionCounts[ta_state.character] &&
                ta_native_pose.animationBlend >= 0.0f && ta_native_pose.animationBlend < 1.0f) {
                TA_NativeAction* prev = &nativeActions[ta_state.character][ta_native_pose.previousActionIndex];
                // Original transitions blend compatible hierarchies; topology changes
                // (for example curled Sonic) select their own root immediately.
                if (prev->nodes == nodes && prev->clip.tracks) {
                    previousAction = prev;
                    blend = ta_native_pose.animationBlend;
                }
            }
        }
    }
    int emote=ta_emote_frame();
    if(emote){nodes=model->nodes;nodeCount=model->count;anim=&model->clips[0];frame=0;previousAction=NULL;}
    Matrix_Push();
    Matrix_Translate(p->actor.world.pos.x, p->actor.world.pos.y, p->actor.world.pos.z, MTXMODE_NEW);
    // Convert the original guest model transform, including its collision-centre
    // offset. Player task position is the feet/body anchor, not the model origin.
    Matrix_RotateYS(-0x4000, MTXMODE_APPLY);
    if (useNative) {
        s16 tiltX=ta_native_pose.rotationX,tiltZ=ta_native_pose.rotationZ;
        if (ta_state.character==TA_SONIC) {
            if (!sonicTiltValid || sonicTiltEpoch!=ta_native_pose.epoch || sonicTiltScene!=ta_native_pose.scene) {
                sonicTiltX=tiltX;sonicTiltZ=tiltZ;sonicTiltValid=1;
            } else if (sonicTiltFrame!=ta_native_pose.hostFrame) {
                // Visual banking eases per simulation tick. Collision and native
                // velocity retain their exact normals; repeated snapshots cannot
                // keep easing or change the physical player position.
                sonicTiltX+=(s16)(tiltX-sonicTiltX)/2;
                sonicTiltZ+=(s16)(tiltZ-sonicTiltZ)/2;
            }
            sonicTiltFrame=ta_native_pose.hostFrame;sonicTiltEpoch=ta_native_pose.epoch;sonicTiltScene=ta_native_pose.scene;
            tiltX=sonicTiltX;tiltZ=sonicTiltZ;
        } else sonicTiltValid=0;
        Matrix_RotateZS(tiltZ, MTXMODE_APPLY);
        Matrix_RotateXS(tiltX, MTXMODE_APPLY);
    }
    f32 modelOffsets[] = {0, 5.4f, 4.5f, 5.98f, 5.0f, 8.0f, 14.02f};
    f32 offset = useNative ? ta_native_pose.modelOffsetY : modelOffsets[ta_state.character];
    if (useNative && ta_state.character == TA_KNUCKLES) offset += .28f;
    if (useNative && ta_state.character == TA_GAMMA) offset += .02f;
    if (!(offset >= 0.0f && offset < 100.0f)) offset = 0;
    Matrix_Translate(0, offset * (useNative ? 2.8f : ta_roster[ta_state.character].modelScale), 0, MTXMODE_APPLY);
    // All six extracted model roots use the same facing basis. The previous
    // Sonic-only half-turn left the remaining roster looking backwards.
    Matrix_RotateYS(0x8000 + p->actor.shape.rot.y, MTXMODE_APPLY);
    f32 scale = useNative ? 2.8f : ta_roster[ta_state.character].modelScale;
    Matrix_Scale(scale, scale, scale, MTXMODE_APPLY);
    if(useNative && ta_state.character==TA_BIG){
        if(ta_native_pose.renderFlags&TA_RENDER_BIG_WINDUP)Matrix_Scale(.9f,1.12f,.9f,MTXMODE_APPLY);
        else if(ta_native_pose.renderFlags&TA_RENDER_BIG_SLAM)Matrix_Scale(1.1f,.9f,1.1f,MTXMODE_APPLY);
        else if(ta_native_pose.renderFlags&TA_RENDER_BIG_IMPACT)Matrix_Scale(1.08f,.94f,1.08f,MTXMODE_APPLY);
    }
    // The extracted curled action already supplies Sonic's ball pose. Additional
    // root squash/roll distorted it, especially when charge transitioned to dash.
    if (renderRoots[ta_state.character]!=nodes) {
        renderRoots[ta_state.character]=nodes;renderGenerations[ta_state.character]++;
    }
    MtxF root;
    Matrix_Get(&root);
    OPEN_DISPS(play->state.gfxCtx);
    gEXEnable(POLY_OPA_DISP++);
    gEXSetRDRAMExtended(POLY_OPA_DISP++, 1);
    Gfx_SetupDL25_Opa(play->state.gfxCtx);
    POLY_OPA_DISP = ta_model_pipeline(POLY_OPA_DISP);
    for (s32 i = 0; i < nodeCount; i++) {
        TA_ModelNode* n = &nodes[i];
        Vec3f pos = n->pos;
        Vec3s rot = n->ang;
        Vec3f nodeScale = n->scale;
        if (anim->tracks && n->animIndex >= 0) sample_track(&anim->tracks[n->animIndex], frame, &pos, &rot);
        if (anim->tracks && n->animIndex >= 0) sample_scale(&anim->tracks[n->animIndex], frame, &nodeScale);
        if (previousAction && n->animIndex >= 0) {
            Vec3f oldPos = n->pos, oldScale = n->scale;
            Vec3s oldRot = n->ang;
            TA_BoneTrack* t = &previousAction->clip.tracks[n->animIndex];
            sample_track(t, ta_native_pose.previousAnimationFrame, &oldPos, &oldRot);
            sample_scale(t, ta_native_pose.previousAnimationFrame, &oldScale);
            pos.x = oldPos.x + (pos.x - oldPos.x) * blend;
            pos.y = oldPos.y + (pos.y - oldPos.y) * blend;
            pos.z = oldPos.z + (pos.z - oldPos.z) * blend;
            rot.x = oldRot.x + (s16)(rot.x - oldRot.x) * blend;
            rot.y = oldRot.y + (s16)(rot.y - oldRot.y) * blend;
            rot.z = oldRot.z + (s16)(rot.z - oldRot.z) * blend;
            nodeScale.x = oldScale.x + (nodeScale.x - oldScale.x) * blend;
            nodeScale.y = oldScale.y + (nodeScale.y - oldScale.y) * blend;
            nodeScale.z = oldScale.z + (nodeScale.z - oldScale.z) * blend;
        }
        if (useNative && ta_state.character==TA_TAILS && (ta_native_pose.renderFlags&TA_RENDER_TAILS_ROTOR) &&
            (i==59 || i==63)) {
            rot.x=(s16)(ta_native_pose.renderFlags>>TA_RENDER_ROTOR_SHIFT);
            rot.z=-0x800; // Tails_Display's original rotor mounting angle.
        }
        int wave=ta_state.character==TA_BIG ? ta_big_emote_frame() : 0;
        if(wave && nodeCount==73){
            f32 weight=wave<6 ? wave/6.0f : wave>35 ? (41-wave)/6.0f : 1.0f;
            if(n->animIndex==28)rot.z+=(s16)((s16)(-0x3000-rot.z)*weight);
            if(n->animIndex==29)rot.z+=(s16)((0x1800+Math_SinS(wave*6500)*0x1000)*weight);
            if(n->animIndex==30)rot.x+=(s16)(Math_SinS(wave*6500)*0x1800*weight);
        }
        if(emote)ta_emote_pose(ta_state.character,n->animIndex,emote,&rot);
        Matrix_Put(n->parent < 0 ? &root : &nodeMatrices[n->parent]);
        if (!(n->flags & 1) || (anim->tracks && n->animIndex >= 0 && anim->tracks[n->animIndex].posCount)) Matrix_Translate(pos.x, pos.y, pos.z, MTXMODE_APPLY);
        if (emote || !(n->flags & 2) || (anim->tracks && n->animIndex >= 0 && anim->tracks[n->animIndex].rotCount)) {
            if (n->flags & 32) {
                Matrix_RotateYS(rot.y, MTXMODE_APPLY);
                Matrix_RotateXS(rot.x, MTXMODE_APPLY);
                Matrix_RotateZS(rot.z, MTXMODE_APPLY);
            } else {
                Matrix_RotateZS(rot.z, MTXMODE_APPLY);
                Matrix_RotateYS(rot.y, MTXMODE_APPLY);
                Matrix_RotateXS(rot.x, MTXMODE_APPLY);
            }
        }
        if (!(n->flags & 4) || (anim->tracks && n->animIndex >= 0 && anim->tracks[n->animIndex].scaleCount))
            Matrix_Scale(nodeScale.x, nodeScale.y, nodeScale.z, MTXMODE_APPLY);
        Matrix_Get(&nodeMatrices[i]);
        if (n->displayList) {
            Matrix_Scale(1.0f / 256.0f, 1.0f / 256.0f, 1.0f / 256.0f, MTXMODE_APPLY);
                gEXMatrixGroupDecomposed(POLY_OPA_DISP++,0x71000000u+((u32)ta_state.character<<24)+((renderGenerations[ta_state.character]&0xffff)<<8)+i,
                    G_EX_PUSH,G_MTX_MODELVIEW,G_EX_COMPONENT_INTERPOLATE,G_EX_COMPONENT_INTERPOLATE,
                    G_EX_COMPONENT_INTERPOLATE,G_EX_COMPONENT_SKIP,G_EX_COMPONENT_SKIP,
                    G_EX_COMPONENT_SKIP,G_EX_COMPONENT_SKIP,G_EX_ORDER_LINEAR,G_EX_EDIT_NONE);
            MATRIX_FINALIZE_AND_LOAD(POLY_OPA_DISP++, play->state.gfxCtx);
            // Keep the KSEG0 bit: RT64 uses it to bypass segmented addressing.
            // gEXDisplayList masks pointers to 28 bits and loses this marker.
            gSPDisplayList(POLY_OPA_DISP++, n->displayList);
            gEXPopMatrixGroup(POLY_OPA_DISP++,G_MTX_MODELVIEW);
        }
    }
    gDPPipeSync(POLY_OPA_DISP++);
    Gfx_SetupDL25_Opa(play->state.gfxCtx);
    CLOSE_DISPS(play->state.gfxCtx);
    Matrix_Pop();
    if (!ta_model_draw_frames) recomp_printf("[Termina Adventure] First model draw: %s, %d nodes\n", ta_roster[ta_state.character].name, model->count);
    ta_model_draw_frames++;
}
