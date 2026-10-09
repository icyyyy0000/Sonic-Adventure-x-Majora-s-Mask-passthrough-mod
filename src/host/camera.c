#include "characters/roster.h"
#include "modding.h"
#include "z64olib.h"
#include <math.h>
f32 Camera_GetFocalActorHeight(Camera* camera);
// Only ordinary guest cameras follow facing. Link and special modes stay stock.
static Camera* normalCamera;
static VecGeo initialOrbit;
static Vec3f initialAt;
static Camera* swingCamera;
static SwingAnimation* swingWork;
static Vec3f intendedEye,previousAt,previousRelative;
static Camera* previousCamera;
static s16 previousScene,previousSetting;
static u32 previousCharacter;
static int cameraValid,obstacleTicks;
static Camera* followCamera;
static u32 followFrame,finalFrame,followCharacter;
static s16 followScene,followSetting;
static int followValid,turnSign,clearFrames;
static f32 orbitYaw,turnVelocity,orbitPitch,orbitDistance,orbitHeight,contactRadius,lastAllowed;
static Vec3f followBody;
static int guest_camera_allowed(Camera* camera){
    return !ta_menu_open && camera && camera->play && ta_native_owner && ta_native_visual && ta_state.character!=TA_LINK &&
        camera->status==CAM_STATUS_ACTIVE && camera->camId==CAM_ID_MAIN && camera->mode==CAM_MODE_NORMAL &&
        !camera->target && camera->focalActor==&GET_PLAYER(camera->play)->actor &&
        ta_can_control(GET_PLAYER(camera->play),camera->play);
}
static f32 vector_length(Vec3f v){return sqrtf(v.x*v.x+v.y*v.y+v.z*v.z);}
static f32 clamp_value(f32 v,f32 low,f32 high){return v<low?low:v>high?high:v;}
static s16 orbit_angle(f32 v){return (s16)(s32)v;}
static int follow_prepare(Camera* camera,VecGeo* proposal){
    Player* player=GET_PLAYER(camera->play);
    Vec3f body=player->actor.world.pos;
    Vec3f moved={body.x-followBody.x,body.y-followBody.y,body.z-followBody.z};
    int reset=!followValid || followCamera!=camera || followScene!=camera->play->sceneId ||
        followSetting!=camera->setting || followCharacter!=ta_state.character ||
        camera->play->gameplayFrames<followFrame || vector_length(moved)>1000;
    f32 radius=camera->dist>20 ? camera->dist : proposal->r;
    radius=clamp_value(radius*1.15f,140,690);
    f32 pitch=clamp_value(camera->paramData.norm1.roData.unk_20,-0x2AAA,0x2AAA);
    f32 focalHeight=Camera_GetFocalActorHeight(camera);
    if(focalHeight<60)focalHeight=60;
    f32 height=body.y+focalHeight+camera->paramData.norm1.roData.unk_00+12;
    if(reset){
        orbitYaw=initialOrbit.r>1 ? initialOrbit.yaw : (s16)(player->actor.shape.rot.y+0x8000);
        orbitPitch=pitch;orbitDistance=radius;orbitHeight=initialAt.y;
        contactRadius=lastAllowed=radius;turnVelocity=0;turnSign=1;clearFrames=0;
        followCamera=camera;followScene=camera->play->sceneId;followSetting=camera->setting;
        followCharacter=ta_state.character;followValid=1;followFrame=finalFrame=camera->play->gameplayFrames-1;
    }
    int advance=followFrame!=camera->play->gameplayFrames;
    if(advance){
        s32 delta=(s16)(player->actor.shape.rot.y+0x8000-orbit_angle(orbitYaw));
        // At the +/-180 degree seam, small heading noise must not reverse the orbit.
        if(delta>30000 || delta< -30000){
            if(turnSign>0 && delta<0)delta+=65536;
            if(turnSign<0 && delta>0)delta-=65536;
        }
        if(delta>256 || delta< -256){
            f32 maximum=ta_settings[14]*65.536f;
            f32 wanted=clamp_value(delta*(ta_settings[14]/125.0f),-maximum,maximum);
            turnVelocity+=(wanted-turnVelocity)*(.35f+ta_settings[14]*.003f);
            if(turnVelocity*delta>0 && fabsf(turnVelocity)>fabsf((f32)delta))turnVelocity=delta;
            orbitYaw+=turnVelocity;
            if(fabsf(turnVelocity)>32)turnSign=turnVelocity>0?1:-1;
        }else turnVelocity=0;
        // Keep the floating angle bounded without jumping across the signed seam.
        if(orbitYaw>65536)orbitYaw-=65536;if(orbitYaw< -65536)orbitYaw+=65536;
        orbitPitch+=(pitch-orbitPitch)*.2f;orbitDistance+=(radius-orbitDistance)*.2f;
        orbitHeight=clamp_value(orbitHeight+(height-orbitHeight)*.35f,height-80,height+80);
        followFrame=camera->play->gameplayFrames;followBody=body;
    }
    proposal->yaw=orbit_angle(orbitYaw);proposal->pitch=orbit_angle(orbitPitch);proposal->r=orbitDistance;
    return advance;
}
static Vec3f camera_ray(Camera* camera,Vec3f candidate){
    Vec3f hit;CollisionPoly* poly=NULL;s32 bgId;
    if(BgCheck_CameraLineTest1(&camera->play->colCtx,&camera->at,&candidate,&hit,&poly,true,true,true,-1,&bgId)){
        Vec3f v={hit.x-camera->at.x,hit.y-camera->at.y,hit.z-camera->at.z};
        f32 d=vector_length(v),margin=d*.5f<8?d*.5f:8;
        if(d<.001f){
            v=(Vec3f){candidate.x-camera->at.x,candidate.y-camera->at.y,candidate.z-camera->at.z};
            f32 length=vector_length(v),s=length>.001f?.1f/length:0;
            return (Vec3f){camera->at.x+v.x*s,camera->at.y+v.y*s,camera->at.z+(length>.001f?v.z*s:.1f)};
        }
        f32 scale=d>.001f?(d-margin)/d:0;
        candidate=(Vec3f){camera->at.x+v.x*scale,camera->at.y+v.y*scale,camera->at.z+v.z*scale};
    }
    return candidate;
}
static Vec3f camera_safe_eye(Camera* camera,Vec3f candidate){
    candidate=camera_ray(camera,candidate);
    CollisionPoly* poly=NULL;s32 bgId;
    f32 floor=BgCheck_CameraRaycastFloor2(&camera->play->colCtx,&poly,&bgId,&candidate);
    if(floor!=BGCHECK_Y_MIN && candidate.y<floor+5){candidate.y=floor+5;candidate=camera_ray(camera,candidate);}
    return candidate;
}
RECOMP_HOOK("Camera_CalcDefaultSwing") void ta_camera_swing_enter(Camera* camera,VecGeo* current,VecGeo* target,
    f32 distance,f32 rate,SwingAnimation* swing,s16* flags){
    swingCamera=NULL;swingWork=NULL;
    if(!guest_camera_allowed(camera)){cameraValid=followValid=0;return;}
    if(ta_settings[14] && normalCamera==camera && current){
        follow_prepare(camera,current);
        camera->eyeNext=OLib_AddVecGeoToVec3f(&camera->at,current);
        return; // Following is finalized once, after every Normal1 branch.
    }
    if(!ta_settings[1]){cameraValid=0;return;}
    swingCamera=camera;swingWork=swing;intendedEye=camera->eyeNext;
}
RECOMP_HOOK_RETURN("Camera_CalcDefaultSwing") void ta_camera_swing_leave(void){
    Camera* camera=swingCamera;if(!camera || !swingWork)return;
    Vec3f relative={camera->eye.x-camera->at.x,camera->eye.y-camera->at.y,camera->eye.z-camera->at.z};
    Vec3f moved={camera->at.x-previousAt.x,camera->at.y-previousAt.y,camera->at.z-previousAt.z};
    if(!cameraValid || previousCamera!=camera || previousScene!=camera->play->sceneId ||
       previousSetting!=camera->setting || previousCharacter!=ta_state.character || vector_length(moved)>1000){
        cameraValid=1;obstacleTicks=0;
    }else{
        Vec3f clipped={camera->eye.x-intendedEye.x,camera->eye.y-intendedEye.y,camera->eye.z-intendedEye.z};
        if(swingWork->unk_64 || vector_length(clipped)>2)obstacleTicks=8;
        if(obstacleTicks){
            f32 oldRadius=vector_length(previousRelative),radius=vector_length(relative);
            Vec3f smoothed={previousRelative.x+(relative.x-previousRelative.x)*.35f,
                previousRelative.y+(relative.y-previousRelative.y)*.35f,previousRelative.z+(relative.z-previousRelative.z)*.35f};
            f32 desired=radius<oldRadius?radius:oldRadius+(radius-oldRadius)*.25f,length=vector_length(smoothed);
            if(length>1){smoothed.x*=desired/length;smoothed.y*=desired/length;smoothed.z*=desired/length;}
            else smoothed=relative;
            Vec3f candidate={camera->at.x+smoothed.x,camera->at.y+smoothed.y,camera->at.z+smoothed.z};
            candidate=camera_ray(camera,candidate);camera->eye=camera->eyeNext=candidate;
            relative=(Vec3f){candidate.x-camera->at.x,candidate.y-camera->at.y,candidate.z-camera->at.z};obstacleTicks--;
        }
    }
    previousCamera=camera;previousAt=camera->at;previousRelative=relative;
    previousScene=camera->play->sceneId;previousSetting=camera->setting;previousCharacter=ta_state.character;
    swingCamera=NULL;swingWork=NULL;
}
RECOMP_HOOK("Camera_Normal1") void ta_camera_normal_enter(Camera* camera){
    normalCamera=camera;if(camera){initialOrbit=OLib_Vec3fDiffToVecGeo(&camera->at,&camera->eye);initialAt=camera->at;}
}
RECOMP_HOOK_RETURN("Camera_Normal1") void ta_camera_normal_leave(void){
    Camera* camera=normalCamera;normalCamera=NULL;
    if(!ta_settings[14] || !guest_camera_allowed(camera)){followValid=0;return;}
    // Final ownership prevents stock corner yaw, pitch and high-speed roll from
    // fighting the follow orbit. Player collision and movement are untouched.
    VecGeo proposal=OLib_Vec3fDiffToVecGeo(&camera->at,&camera->eyeNext);
    follow_prepare(camera,&proposal);
    int advance=finalFrame!=camera->play->gameplayFrames;
    finalFrame=camera->play->gameplayFrames;
    Player* player=GET_PLAYER(camera->play);
    camera->at=(Vec3f){player->actor.world.pos.x,orbitHeight,player->actor.world.pos.z};
    camera->focalActorAtOffset=(Vec3f){0,orbitHeight-player->actor.world.pos.y,0};
    Vec3f candidate=camera_safe_eye(camera,OLib_AddVecGeoToVec3f(&camera->at,&proposal));
    Vec3f v={candidate.x-camera->at.x,candidate.y-camera->at.y,candidate.z-camera->at.z};
    f32 allowed=vector_length(v);
    // Always shorten immediately. Require three clear frames before easing back
    // out so a grazing wall does not alternate full/short distance every tick.
    if(allowed<contactRadius){contactRadius=allowed;clearFrames=0;}
    else if(advance){
        clearFrames=fabsf(allowed-lastAllowed)>2 ? 1 : clearFrames+1;
        if(clearFrames>=3)contactRadius+=(allowed-contactRadius)*.2f;
    }
    if(advance)lastAllowed=allowed;
    if(allowed>.001f && contactRadius<allowed){f32 s=contactRadius/allowed;v.x*=s;v.y*=s;v.z*=s;}
    candidate=(Vec3f){camera->at.x+v.x,camera->at.y+v.y,camera->at.z+v.z};
    camera->eye=camera->eyeNext=camera_safe_eye(camera,candidate);
    camera->roll=0;camera->atLerpStepScale=1;
    VecGeo direction=OLib_Vec3fDiffToVecGeo(&camera->eye,&camera->at);
    camera->inputDir.x=direction.pitch;camera->inputDir.y=orbit_angle(orbitYaw+0x8000);camera->inputDir.z=0;
}
