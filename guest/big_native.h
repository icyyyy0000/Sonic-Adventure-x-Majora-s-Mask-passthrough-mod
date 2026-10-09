#ifndef TA_BIG_NATIVE_H
#define TA_BIG_NATIVE_H
// New Big abilities still move through the original task and streamed collision.
static unsigned bigNativeMode,bigNativeCommand,bigImpactSequence,bigImpactFrames,bigBlockedSteps,bigAbilitySteps;
static NJS_VECTOR bigLastPosition,bigRequestedVelocity;
static void ta_big_native_reset(){bigNativeMode=bigNativeCommand=bigImpactFrames=bigBlockedSteps=bigAbilitySteps=0;}
static void ta_big_native_before(const TA_HostFrame& host,EntityData1* p,CharObj2* state) {
    unsigned requested=(host.flags&TA_HOST_BIG_GRAPPLE) ? 1 : (host.flags&TA_HOST_BIG_SLAM) ? 2 : (host.flags&TA_HOST_BIG_EMOTE) ? 3 : 0;
    if(!requested){bigNativeMode=0;return;}
    if(host.targetId!=bigNativeCommand){bigNativeCommand=host.targetId;bigNativeMode=requested;bigBlockedSteps=bigAbilitySteps=0;}
    if(!bigNativeMode)return;
    if(++bigAbilitySteps>720){bigNativeMode=0;return;}
    if(bigNativeMode==3){
        if(bigAbilitySteps>150 || !(p->Status&Status_Ground)){bigNativeMode=0;return;}
        p->Action=1;state->Speed={0,0,0};bigLastPosition=p->Position;return;
    }
    NJS_VECTOR velocity{};
    if(bigNativeMode==1){
        float x=host.targetPosition[0]-p->Position.x,y=host.targetPosition[1]-p->Position.y,z=host.targetPosition[2]-p->Position.z;
        float distance=std::sqrt(x*x+y*y+z*z);
        if(!std::isfinite(distance) || distance<6 || distance>1000){bigNativeMode=0;state->Speed={0,0,0};return;}
        float maxSpeed=host.targetRadius>=3 && host.targetRadius<=9 ? host.targetRadius : 6;
        float speed=distance<maxSpeed*4 ? distance*.25f : maxSpeed;
        velocity={x*speed/distance,y*speed/distance,z*speed/distance};
        if(x*x+z*z>.1f)p->Rotation.y=static_cast<int>(std::atan2(z,x)*10430.37835f);
    } else velocity=bigAbilitySteps<=18 ? NJS_VECTOR{0,.08f,0} : NJS_VECTOR{0,-8,0};
    bigRequestedVelocity=velocity;
    p->Action=8;p->Status&=~(Status_Ground|Status_OnColli);
    p->Rotation.x=p->Rotation.z=0;
    reinterpret_cast<void(__cdecl*)(EntityData1*,NJS_VECTOR*)>(0x43EC00)(p,&velocity);state->Speed=velocity;
    bigLastPosition=p->Position;
}
static void ta_big_native_commit(EntityData1* p,CharObj2* state,const NJS_VECTOR& start){
    if(bigNativeMode!=1 && bigNativeMode!=2)return;
    p->Position={start.x+bigRequestedVelocity.x,start.y+bigRequestedVelocity.y,start.z+bigRequestedVelocity.z};
    NJS_VECTOR speed=bigRequestedVelocity;
    reinterpret_cast<void(__cdecl*)(EntityData1*,NJS_VECTOR*)>(0x43EC00)(p,&speed);state->Speed=speed;
    p->Status&=~(Status_Ground|Status_OnColli);
}
static void ta_big_native_after(EntityData1* p) {
    if(bigImpactFrames)--bigImpactFrames;
    if(!bigNativeMode)return;
    float x=p->Position.x-bigLastPosition.x,y=p->Position.y-bigLastPosition.y,z=p->Position.z-bigLastPosition.z;
    if(bigNativeMode==2 && bigAbilitySteps>18 && (p->Status&Status_Ground)) {bigNativeMode=0;++bigImpactSequence;bigImpactFrames=12;return;}
    if(bigNativeMode==3 || (bigNativeMode==2 && bigAbilitySteps<=18))return;
    if(x*x+y*y+z*z<.0025f)++bigBlockedSteps;else bigBlockedSteps=0;
    if(bigBlockedSteps>15)bigNativeMode=0;
}
static unsigned ta_big_render_flags(){return (bigNativeMode==1 ? TA_RENDER_BIG_GRAPPLE : bigNativeMode==2 ? TA_RENDER_BIG_SLAM | (bigAbilitySteps<=18 ? TA_RENDER_BIG_WINDUP : 0) : bigNativeMode==3 ? TA_RENDER_BIG_EMOTE : 0)|(bigImpactFrames ? TA_RENDER_BIG_IMPACT : 0);}
#endif
