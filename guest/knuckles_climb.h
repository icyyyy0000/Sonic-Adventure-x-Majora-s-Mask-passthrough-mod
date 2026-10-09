#ifndef TA_KNUCKLES_CLIMB_H
#define TA_KNUCKLES_CLIMB_H
static bool knucklesClinging;
static unsigned knucklesReleaseSteps;
static float knucklesClimbFrame;
struct TA_ClimbSurface {NJS_VECTOR point,normal;};
static bool ta_climb_surface(const TA_WorldFrame& world,NJS_VECTOR center,float reach,TA_ClimbSurface& hit) {
    float best=reach;
    bool found=false;
    for(unsigned i=0;i<world.count && i<TA_WORLD_CAPACITY;i++) {
        auto& t=world.triangles[i];if(!(t.flags&TA_SURFACE_SOLID))continue;
        auto a=t.vertices;auto b=a+3;auto c=b+3;
        NJS_VECTOR u{b[0]-a[0],b[1]-a[1],b[2]-a[2]},v{c[0]-a[0],c[1]-a[1],c[2]-a[2]};
        NJS_VECTOR n{u.y*v.z-u.z*v.y,u.z*v.x-u.x*v.z,u.x*v.y-u.y*v.x};
        float len=std::sqrt(n.x*n.x+n.y*n.y+n.z*n.z);if(len<.00001f)continue;
        n.x/=len;n.y/=len;n.z/=len;
        float distance=(center.x-a[0])*n.x+(center.y-a[1])*n.y+(center.z-a[2])*n.z;
        if(distance<0){distance=-distance;n.x=-n.x;n.y=-n.y;n.z=-n.z;}
        if(distance>best || n.y>.7f)continue; // standing floors are not a wall latch
        NJS_VECTOR point{center.x-n.x*distance,center.y-n.y*distance,center.z-n.z*distance};
        NJS_VECTOR w{point.x-a[0],point.y-a[1],point.z-a[2]};
        float uu=u.x*u.x+u.y*u.y+u.z*u.z,uv=u.x*v.x+u.y*v.y+u.z*v.z,vv=v.x*v.x+v.y*v.y+v.z*v.z;
        float wu=w.x*u.x+w.y*u.y+w.z*u.z,wv=w.x*v.x+w.y*v.y+w.z*v.z,den=uu*vv-uv*uv;
        if(std::fabs(den)<.00001f)continue;
        float s=(wu*vv-wv*uv)/den,q=(wv*uu-wu*uv)/den;
        if(s<-.0001f || q<-.0001f || s+q>1.0001f)continue;
        hit={point,n};best=distance;found=true;
    }
    return found;
}
static bool ta_knuckles_climb(const TA_WorldFrame& world,const TA_HostFrame& host,EntityData1* p,CharObj2* state,unsigned pressed) {
    if(knucklesReleaseSteps)--knucklesReleaseSteps;
    float centerHeight=state->PhysicsData.YOff,radius=state->PhysicsData.RippleSize;
    float reach=radius+2>centerHeight+2 ? radius+2 : centerHeight+2;
    if(radius<.1f || radius>20)return false;
    TA_ClimbSurface surface;
    NJS_VECTOR center{p->Position.x,p->Position.y+centerHeight,p->Position.z};
    bool held=(host.buttons&0x8000)!=0;
    if(!held || (pressed&Buttons_B) || knucklesReleaseSteps ||
        (!knucklesClinging && (p->Status&Status_Ground)) || !ta_climb_surface(world,center,reach,surface)) {
        if(knucklesClinging) {
            p->Action=9;p->Status&=~(Status_Ground|Status_OnColli);state->Speed={0,0,0};
            knucklesReleaseSteps=12;
        }
        knucklesClinging=false;return false;
    }
    NJS_VECTOR n=surface.normal;
    NJS_VECTOR up{-n.x*n.y,1-n.y*n.y,-n.z*n.y};
    float len=std::sqrt(up.x*up.x+up.y*up.y+up.z*up.z);
    if(len<.05f) {float angle=host.cameraYaw/10430.37835f;up={std::cos(angle),0,std::sin(angle)};}
    else {up.x/=len;up.y/=len;up.z/=len;}
    NJS_VECTOR right{up.y*n.z-up.z*n.y,up.z*n.x-up.x*n.z,up.x*n.y-up.y*n.x};
    unsigned setting=(host.flags>>TA_HOST_SPEED_SHIFT)&TA_HOST_PERCENT_MASK;
    float factor=setting>=1 && setting<=12 ? setting*.25f : 1;
    float y=host.stickY/80.0f*.8f*factor,x=host.stickX/80.0f*.8f*factor;
    NJS_VECTOR candidate{center.x+up.x*y+right.x*x,center.y+up.y*y+right.y*x,center.z+up.z*y+right.z*x};
    TA_ClimbSurface next;
    if(!ta_climb_surface(world,candidate,reach,next)) {knucklesClinging=false;p->Action=9;return false;}
    float clearance=next.normal.y<-.7f ? state->PhysicsData.CollisionSize*.5f : radius;
    p->Position={next.point.x+next.normal.x*clearance,next.point.y+next.normal.y*clearance-centerHeight,next.point.z+next.normal.z*clearance};
    p->Rotation.y=static_cast<int>(std::atan2(-n.z,-n.x)*10430.37835f);
    p->Rotation.x=n.y<-.7f ? 32768 : 0;p->Rotation.z=0;
    p->Action=9;p->Status&=~(Status_Ground|Status_OnColli);state->Speed={};
    knucklesClinging=true;knucklesClimbFrame+=std::fabs(x)+std::fabs(y);
    return true;
}
#endif
