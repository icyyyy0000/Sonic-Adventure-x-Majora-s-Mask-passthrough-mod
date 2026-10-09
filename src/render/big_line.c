#include "characters/roster.h"
#include "render/model_pipeline.h"
#include "modding.h"
static Actor* lineActor;static PlayState* linePlay;
RECOMP_HOOK("Player_Draw") void ta_big_line_enter(Actor* actor,PlayState* play){lineActor=actor;linePlay=play;}
RECOMP_HOOK_RETURN("Player_Draw") void ta_big_line_draw(void){
    Vec3f end;
    if(!lineActor || lineActor!=&GET_PLAYER(linePlay)->actor || ta_state.character!=TA_BIG || !ta_big_line(&end))return;
    PlayState* play=linePlay;Vec3f origin=lineActor->world.pos;
    s16 yaw=lineActor->shape.rot.y;
    f32 sx=Math_SinS(yaw),cz=Math_CosS(yaw);
    Vec3f hand={origin.x+sx*20+cz*20,origin.y+36,origin.z+cz*20-sx*20};
    Vec3f tip={hand.x+sx*35,hand.y+32,hand.z+cz*35};
    Vec3f starts[]={hand,tip},ends[]={tip,end};
    Matrix_Push();Matrix_Translate(origin.x,origin.y,origin.z,MTXMODE_NEW);
    OPEN_DISPS(play->state.gfxCtx);
    POLY_OPA_DISP=ta_model_pipeline(POLY_OPA_DISP);
    gSPTexture(POLY_OPA_DISP++,0,0,0,0,G_OFF);gDPSetCombineMode(POLY_OPA_DISP++,G_CC_PRIMITIVE,G_CC_PRIMITIVE);
    MATRIX_FINALIZE_AND_LOAD(POLY_OPA_DISP++,play->state.gfxCtx);
    s16 cameraYaw=Camera_GetInputDirYaw(GET_ACTIVE_CAM(play));
    for(int segment=0;segment<2;segment++){
        f32 width=segment==0 ? 1.8f : .65f;
        f32 dx=Math_CosS(cameraYaw)*width,dz=-Math_SinS(cameraYaw)*width;
        Vtx* vertices=GRAPH_ALLOC(play->state.gfxCtx,sizeof(Vtx)*4);
        Vec3f a=starts[segment],b=ends[segment];
        for(int i=0;i<4;i++){
            Vec3f pos=i<2 ? a : b;f32 sign=(i==0 || i==3) ? -1 : 1;
            vertices[i]=(Vtx){{{(s16)(pos.x-origin.x+dx*sign),(s16)(pos.y-origin.y),(s16)(pos.z-origin.z+dz*sign)},0,{0,0},{255,255,255,255}}};
        }
        if(segment==0)gDPSetPrimColor(POLY_OPA_DISP++,0,0,130,88,46,255);
        else gDPSetPrimColor(POLY_OPA_DISP++,0,0,245,235,180,255);
        gSPVertex(POLY_OPA_DISP++,vertices,4,0);gSP2Triangles(POLY_OPA_DISP++,0,1,2,0,0,2,3,0);
    }
    gDPPipeSync(POLY_OPA_DISP++);Gfx_SetupDL25_Opa(play->state.gfxCtx);
    CLOSE_DISPS(play->state.gfxCtx);Matrix_Pop();
}
