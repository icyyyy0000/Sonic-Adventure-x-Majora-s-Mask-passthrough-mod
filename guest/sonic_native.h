#ifndef TA_SONIC_NATIVE_H
#define TA_SONIC_NATIVE_H
// Supply one host-validated enemy to the original homing algorithm. The proxy
// has owned CCI data and contains no host game pointers or executable task.
static EntityData1 homingProxy;
static CollisionInfo homingProxyInfo;
static CollisionData homingProxyShape;
static uint32_t sonicHitSequence,sonicHitTarget;
struct TA_HomingScope {
    HomingAttackTarget saved[2];
    unsigned short count;
    bool enabled;
    TA_HomingScope(const TA_HostFrame& host,EntityData1* player) {
        enabled=host.character==1;
        if (!enabled) return;
        auto list=reinterpret_cast<HomingAttackTarget*>(0x3B259C0);
        auto index=reinterpret_cast<unsigned short*>(0x3B23288);
        saved[0]=list[0];saved[1]=list[1];count=*index;
        list[0]={};list[1]={};*index=0;
        if (host.character!=1 || !(host.flags&TA_HOST_HOMING_TARGET) || !host.targetId) return;
        for (float v:host.targetPosition) if (!std::isfinite(v) || std::fabs(v)>1000000) return;
        homingProxy={};homingProxyInfo={};homingProxyShape={};
        homingProxy.Position={host.targetPosition[0],host.targetPosition[1],host.targetPosition[2]};
        homingProxy.CollisionInfo=&homingProxyInfo;
        homingProxyInfo.id=2;homingProxyInfo.nbInfo=1;homingProxyInfo.CollisionArray=&homingProxyShape;
        homingProxyShape.attr=0x20; // absolute centre, as read at Sonic 0x49242D
        homingProxyShape.center=homingProxy.Position;
        homingProxyShape.a=host.targetRadius;
        float dx=homingProxy.Position.x-player->Position.x;
        float dy=homingProxy.Position.y-player->Position.y;
        float dz=homingProxy.Position.z-player->Position.z;
        list[0]={&homingProxy,dx*dx+dy*dy+dz*dz};*index=1;
    }
    ~TA_HomingScope() {
        if (!enabled) return;
        auto list=reinterpret_cast<HomingAttackTarget*>(0x3B259C0);
        list[0]=saved[0];list[1]=saved[1];
        *reinterpret_cast<unsigned short*>(0x3B23288)=count;
    }
};
static bool ta_sonic_hit_segment(const NJS_VECTOR& start,const NJS_VECTOR& end,
                                 const TA_HostFrame& host,NJS_VECTOR& contact) {
    float dx=end.x-start.x,dy=end.y-start.y,dz=end.z-start.z;
    float length=dx*dx+dy*dy+dz*dz;
    if (length<.000001f) return false;
    float t=((host.targetPosition[0]-start.x)*dx+(host.targetPosition[1]-start.y)*dy+
             (host.targetPosition[2]-start.z)*dz)/length;
    if (t<0) t=0;if (t>1) t=1;
    contact={start.x+t*dx,start.y+t*dy,start.z+t*dz};
    float x=contact.x-host.targetPosition[0],y=contact.y-host.targetPosition[1],z=contact.z-host.targetPosition[2];
    float radius=host.targetRadius>2 && host.targetRadius<20 ? host.targetRadius : 10;
    return x*x+y*y+z*z<=radius*radius;
}
static void ta_sonic_homing_contact(const TA_HostFrame& host,EntityData1* p,CharObj2* state,
                                    ObjectMaster* obj,const NJS_VECTOR& before,unsigned oldAction) {
    if (host.character!=1 || !(host.flags&TA_HOST_HOMING_TARGET) || !host.targetId ||
        (oldAction!=14 && p->Action!=14)) return;
    NJS_VECTOR contact;
    if (!ta_sonic_hit_segment(before,p->Position,host,contact)) return;
    p->Position=contact;p->Action=8;p->NextAction=0;
    p->Status=(p->Status & ~(Status_Ground|Status_OnColli|Status_Hurt))|Status_Ball|Status_Attack;
    state->NoControlTime=0;state->LightdashTime=state->LightdashTimer=0;
    NJS_VECTOR bounce={0,state->PhysicsData.JumpSpeed,0};
    if (obj->Data2) reinterpret_cast<EntityData2*>(obj->Data2)->VelocityDirection=bounce;
    reinterpret_cast<void(__cdecl*)(EntityData1*,NJS_VECTOR*)>(0x43EC00)(p,&bounce);
    state->Speed=bounce;
    sonicHitTarget=host.targetId;++sonicHitSequence;
}
static int ta_sonic_render_index(CharObj2* state,EntityData1* p) {
    auto& anim=state->AnimationThing;
    int index=anim.State==2 ? anim.LastIndex : anim.Index;
    // Exact selection made by Sonic_Display 0x494AD1..0x494AF9.
    if (anim.State!=2 && (p->Status&Status_Ball) && index!=145 && (state->SonicSpinTimer&0x11)) index=32;
    return index;
}
#endif
