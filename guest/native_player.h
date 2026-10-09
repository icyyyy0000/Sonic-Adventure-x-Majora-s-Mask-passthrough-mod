#ifndef TA_NATIVE_PLAYER_H
#define TA_NATIVE_PLAYER_H
#include "world_contacts.h"
#include "sonic_native.h"
#include "native_audio.h"
#include "big_native.h"
#include "knuckles_climb.h"
// Invoke the loaded original character task against a scoped Zelda-only land
// collision list. The real game's stage collision state is restored afterward.
struct TA_PhysicsSettingsScope {
    CharObj2* state;float gravity,add;
    TA_PhysicsSettingsScope(CharObj2* s,const TA_HostFrame& host):state(s),gravity(s->PhysicsData.Gravity),add(s->PhysicsData.GravityAdd){
        unsigned setting=(host.flags>>TA_HOST_GRAVITY_SHIFT)&TA_HOST_PERCENT_MASK;
        float factor=setting>=1 && setting<=12 ? setting*.25f : 1;
        state->PhysicsData.Gravity=gravity*factor;state->PhysicsData.GravityAdd=add*factor;
    }
    ~TA_PhysicsSettingsScope(){state->PhysicsData.Gravity=gravity;state->PhysicsData.GravityAdd=add;}
};
struct TA_LandScope {
    DynamicCOL entries[1024], ranged[128];
    COL copies[128];
    short count;
    int rangeCount, copyCount;
    LandTable* table;
    int enabled;
    void** killingEntry;
    void* killingList;
    TA_LandScope(TA_CollisionMirror& mirror) {
        unsigned level=static_cast<unsigned short>(*reinterpret_cast<short*>(0x3B22DCC));
        killingEntry=level<43 ? reinterpret_cast<void**>(0x915908)+level : nullptr;
        killingList=killingEntry ? *killingEntry : nullptr;
        if (killingEntry) *killingEntry=nullptr;
        table=*reinterpret_cast<LandTable**>(0x3B2F718);
        enabled=*reinterpret_cast<int*>(0x915460);
        count=*reinterpret_cast<short*>(0x3B32724);
        rangeCount=*reinterpret_cast<int*>(0x3B36D38);
        copyCount=*reinterpret_cast<int*>(0x3B36D3C);
        memcpy(entries,reinterpret_cast<void*>(0x3B2F720),sizeof(entries));
        memcpy(ranged,reinterpret_cast<void*>(0x3B32728),sizeof(ranged));
        memcpy(copies,reinterpret_cast<void*>(0x3B2E518),sizeof(copies));
        *reinterpret_cast<LandTable**>(0x3B2F718)=&mirror.table;
        *reinterpret_cast<int*>(0x915460)=1;
        *reinterpret_cast<short*>(0x3B32724)=mirror.table.COLCount;
        *reinterpret_cast<int*>(0x3B36D38)=0;
        *reinterpret_cast<int*>(0x3B36D3C)=mirror.table.COLCount;
        auto list=reinterpret_cast<DynamicCOL*>(0x3B2F720);
        auto cache=reinterpret_cast<COL*>(0x3B2E518);
        for (int i=0;i<mirror.table.COLCount;i++) {
            cache[i]=mirror.collision[i];
            list[i]={cache[i].Flags,cache[i].Model,nullptr};
        }
    }
    ~TA_LandScope() {
        if (killingEntry) *killingEntry=killingList;
        memcpy(reinterpret_cast<void*>(0x3B2F720),entries,sizeof(entries));
        memcpy(reinterpret_cast<void*>(0x3B32728),ranged,sizeof(ranged));
        memcpy(reinterpret_cast<void*>(0x3B2E518),copies,sizeof(copies));
        *reinterpret_cast<LandTable**>(0x3B2F718)=table;
        *reinterpret_cast<int*>(0x915460)=enabled;
        *reinterpret_cast<short*>(0x3B32724)=count;
        *reinterpret_cast<int*>(0x3B36D38)=rangeCount;
        *reinterpret_cast<int*>(0x3B36D3C)=copyCount;
    }
};
static ObjectMaster* hookedPlayer;
static ObjectFuncPtr originalPlayerMain;
static bool nativeEnabled=true, nativeActive, nativeSession;
static bool nativeResumeReset;
static bool nativeHeld;
static bool nativeSuspended;
static uint32_t processedFrame, nativeEpoch, nativeScene, previousButtons;
static unsigned nativeCharacter;
static short originalNativeUpgrades;
static unsigned tailsRotorAngle;
static NJS_VECTOR stagePosition;
static Rotation3 stageRotation;
static NJS_VECTOR nativeVelocity;
static void __cdecl ta_native_main(ObjectMaster* obj) {
    if (!originalPlayerMain) return;
    TA_HostFrame host{};
    bool connected=ta_read_host(&host)!=0;
    nativeAudioAllowed=!(host.flags&TA_HOST_MUTE_CHARACTER);
    bool requested=nativeEnabled && connected && host.character && (host.flags & TA_HOST_NATIVE_PHYSICS);
    EntityData1* p=obj->Data1;
    if (p && p->Action==0) { if(connected){TA_SilentAudioScope silence;originalPlayerMain(obj);}else originalPlayerMain(obj);p=obj->Data1; }
    CharObj2* state=physics[0];
    nativeActive=false;
    // Lost heartbeat: hold the foreign-world task instead of restoring the
    // Station Square task at a Zelda coordinate. Explicit Link/off still yields.
    if (!connected && nativeSession) {nativeHeld=nativeSuspended=true;return;}
    if (!requested) {
        if (nativeSession && p && state) {
            if (character_id(p->CharID)==nativeCharacter) state->Upgrades=originalNativeUpgrades;
            p->Position=stagePosition;p->Rotation=stageRotation;p->Action=1;
            p->Status=0;state->Speed={};state->NoControlTime=0;
        }
        nativeSession=false;nativeHeld=nativeSuspended=false;nativeResumeReset=false;previousButtons=processedFrame=0;
        if (connected) {TA_SilentAudioScope silence;originalPlayerMain(obj);}
        else originalPlayerMain(obj);
        return;
    }
    // Freeze when the host is in dialogue, transitioning or awaiting geometry.
    // Never fall back to Station Square collision during a pending takeover.
    if (!(host.flags & TA_HOST_GAMEPLAY) || !p || !state || character_id(p->CharID)!=host.character) {
        // Pausing in the same world is suspended simulation, not a new
        // takeover. Keep the airborne/charge FSM, contact work and momentum.
        if ((host.flags&TA_HOST_PAUSED) && nativeSession && nativeCharacter==host.character &&
            nativeEpoch==host.epoch && nativeScene==host.scene && p && state && character_id(p->CharID)==host.character)
            nativeHeld=nativeSuspended=true;
        else nativeResumeReset=true;
        return;
    }
    if (!ta_read_world(&worldFrame) || worldFrame.epoch!=host.epoch || worldFrame.scene!=host.scene ||
        !ta_refresh_mirror(worldFrame) || !ta_current_mirror().table.COLCount ||
        ta_current_mirror().table.COLCount>128 || (worldFrame.flags & TA_WORLD_TRUNCATED)) {
        // Geometry contention holds momentum. A scene/epoch change still resets
        // normally once a complete matching world arrives.
        nativeHeld=true;
        return;
    }
    bool reset=!nativeSession || nativeResumeReset || nativeEpoch!=host.epoch || nativeScene!=host.scene || nativeCharacter!=host.character ||
        (processedFrame && host.frame<processedFrame);
    if (reset) {
        ta_big_native_reset();
        knucklesClinging=false;knucklesReleaseSteps=0;knucklesClimbFrame=0;
        if (!nativeSession || nativeCharacter!=host.character) originalNativeUpgrades=state->Upgrades;
        if (!nativeSession) {stagePosition=p->Position;stageRotation=p->Rotation;}
        reinterpret_cast<void(__cdecl*)(unsigned char,float,float,float)>(0x441780)(0,host.position[0],host.position[1],host.position[2]);
        p->Rotation={0,static_cast<int>(host.yaw),0};
        p->Action=1;p->NextAction=0;p->Status=0;p->LoopData=nullptr;
        state->Speed={};state->NoControlTime=0;state->Powerups&=~0xc000;state->ObjectHeld=nullptr;state->DynColObject=nullptr;
        // Teleporting the task alone preserves the previous scene's contact work.
        // These owned buffers are csts (132 bytes) and PL_LANDPOSI[15] in the SDK.
        if (state->array_1x132) memset(state->array_1x132,0,132);
        if (state->array_15x32) memset(state->array_15x32,0,15*32);
        state->field_74=0;state->SurfaceFlags=state->SurfaceFlags_Old=0;
        state->SurfaceNormal={0,1,0};state->field_44={};
        state->_struct_a3={};state->_struct_a3.DistanceMin=1000000;
        state->_struct_a3.DistanceMax=-1000000;
        if (obj->Data2) {
            auto motion=reinterpret_cast<EntityData2*>(obj->Data2);
            motion->VelocityDirection={};motion->SomeCollisionVector={};
        }
        nativeEpoch=host.epoch;nativeScene=host.scene;nativeCharacter=host.character;
        processedFrame=previousButtons=0;nativeSession=true;tailsRotorAngle=0;
        nativeResumeReset=false;
        nativeHeld=nativeSuspended=false;
    }
    nativeActive=true;
    // Hover is the original Jet Booster ability. Grant it only in the owned
    // Zelda session; Character Select/SADX progression need not have unlocked it.
    if (host.character==6) state->Upgrades|=Upgrades_JetBooster;
    if (host.character==2) state->Upgrades|=Upgrades_RhythmBadge;
    if (host.character==4) state->Upgrades|=Upgrades_WarriorFeather;
    // Time spent waiting for geometry/heartbeat is frozen simulation time.
    // Preserve speed, but do not release a burst of catchup movement on recovery.
    if (nativeHeld) {processedFrame=host.frame ? host.frame-1 : 0;nativeHeld=false;}
    if (processedFrame==host.frame) return;
    auto controller=reinterpret_cast<ControllerData*>(0x3B0E7F0);
    auto pointer=reinterpret_cast<ControllerData**>(0x3B0E77C);
    auto polar=reinterpret_cast<PolarCoord*>(0x3B0E7A0);
    auto pressed=reinterpret_cast<int*>(0x3B0E354);
    ControllerData backup=*controller;ControllerData* oldPointer=*pointer;
    PolarCoord oldPolar=*polar;int oldHeld=*heldButtons,oldPressed=*pressed;
    unsigned buttons=0;
    if (host.buttons & 0x8000) buttons|=Buttons_A;
    if (host.buttons & 0x4000) buttons|=Buttons_B;
    if (host.character==5 && !(host.flags&TA_HOST_BIG_ROD_ONLY)) buttons&=~Buttons_B; // host distinguishes cast/air tap
    // Menu presses/heartbeat gaps must not become fresh A/B ability edges.
    // Release then press again to request an ability after resuming.
    if (nativeSuspended) {previousButtons=buttons;nativeSuspended=false;}
    // Z is targeting in Zelda; keep it out of the character-selection chords.
    unsigned advanceFrames=processedFrame && host.frame>processedFrame ? host.frame-processedFrame : 1;
    if (advanceFrames>3) advanceFrames=3;
    unsigned nativeSteps=advanceFrames*3;
    NJS_VECTOR before=p->Position;
    {
        TA_LandScope land(ta_current_mirror());
        if (reset && logFile) {
            struct Unit {int found,attr,angx,angz;float height;NJS_VECTOR normal;};
            struct Shadow {NJS_VECTOR pos;Unit lower,upper;} shadow{};
            shadow.pos=p->Position;shadow.lower.height=-1000000;shadow.upper.height=1000000;
            auto probe=reinterpret_cast<int(__cdecl*)(Shadow*,NJS_OBJECT*,unsigned)>(0x455DE0);
            int result=probe(&shadow,&ta_current_mirror().objects[0],ColFlags_Solid);
            fprintf(logFile,"Native collision probe: task=%p, COL=%d, result=%d lower=%d/%f upper=%d/%f\n",originalPlayerMain,ta_current_mirror().table.COLCount,result,shadow.lower.found,shadow.lower.height,shadow.upper.found,shadow.upper.height);fflush(logFile);
        }
        for (unsigned step=0;step<nativeSteps;step++) {
            // Use the engine's own nearby-land preparation for each native step.
            reinterpret_cast<void(__cdecl*)()>(0x43AEF0)();
            controller->HeldButtons=buttons;controller->NotHeldButtons=~buttons;
            controller->PressedButtons=step==0 ? buttons & ~previousButtons : 0;
            controller->ReleasedButtons=step==0 ? previousButtons & ~buttons : 0;
            controller->LeftStickX=host.stickX*127/80;
            controller->LeftStickY=-host.stickY*127/80;
            *pointer=controller;*heldButtons=buttons;*pressed=controller->PressedButtons;
            float magnitude=std::sqrt(float(host.stickX*host.stickX+host.stickY*host.stickY))/80.0f;
            bool dead=host.character==1 ? (std::abs(host.stickX)<=8 && std::abs(host.stickY)<=8) : magnitude<.15f;
            polar->magnitude=dead ? 0 : magnitude>1 ? 1 : magnitude;
            polar->direction=(host.cameraYaw+static_cast<int>(std::atan2(float(host.stickX),float(host.stickY))*10430.37835f)) & 0xffff;
            if (p->CollisionInfo) {
                // Stage contacts are not valid in the mirror. Clear their flags
                // and pointers together: Tails trusts flag 0x10 and dereferences
                // CollidingObject in the original task at 0x45E846.
                auto col=p->CollisionInfo;
                col->nbHit=0;col->flag=0;col->CollidingObject=nullptr;
                col->my_num=col->hit_num=-1;
                for (auto& hit:col->CollisionThings) {hit={};hit.hit_num=-1;}
            }
            // The staging collision queue can stamp damage on the player between
            // frames even after its CCI pointers are cleared. Zelda owns health;
            // discard staging hurt/death signals before the original action FSM.
            p->Status &= ~Status_Hurt;
            state->Powerups &= ~0xc000;
            state->SurfaceFlags &= ~0x10000;
            if(host.character==3 && !(host.flags&TA_HOST_DISABLE_CLIMB) && ta_knuckles_climb(worldFrame,host,p,state,controller->PressedButtons))continue;
            if(host.character==5)ta_big_native_before(host,p,state);
            NJS_VECTOR stepStart=p->Position;
            NJS_VECTOR stepSpeed=state->Speed;
            Rotation3 stepRotation=p->Rotation;
            short stepStatus=p->Status;
            bool wasGrounded=(p->Status&1)!=0;
            unsigned oldAction=static_cast<unsigned char>(p->Action);
            TA_NativeAudioScope audio(host.character);
            {TA_HomingScope homing(host,p);TA_PhysicsSettingsScope settings(state,host);originalPlayerMain(obj);}
            // The owned task does not run Tails_Display: animate its rotor on
            // simulation steps, preserving phase across pauses and duplicate frames.
            if(host.character==2 && p->Action==15)tailsRotorAngle=(tailsRotorAngle+0x2000)&0xffff;
            if(host.character==4 && wasGrounded && !(p->Status&Status_Ground) && (buttons&Buttons_B) && state->Speed.y>.5f){
                unsigned setting=(host.flags>>TA_HOST_AMY_HEIGHT_SHIFT)&TA_HOST_PERCENT_MASK;
                float factor=setting>=1 && setting<=12 ? std::sqrt(setting*.25f) : 1;
                state->Speed.y*=factor;p->Position.y=stepStart.y+(p->Position.y-stepStart.y)*factor;
            }
            if(host.character==5)ta_big_native_commit(p,state,stepStart);
            unsigned speedSetting=(host.flags>>TA_HOST_SPEED_SHIFT)&TA_HOST_PERCENT_MASK;
            float movementScale=speedSetting>=1 && speedSetting<=12 ? speedSetting*.25f : 1;
            if(!(host.character==5 && bigNativeMode)){
                p->Position.x=stepStart.x+(p->Position.x-stepStart.x)*movementScale;
                p->Position.z=stepStart.z+(p->Position.z-stepStart.z)*movementScale;
            }
            float hoverScale=1;
            // Preserve the booster FSM and its vertical speed. Scale only the
            // horizontal hover displacement before the swept collision guards.
            if(host.character==6 && (host.flags&TA_HOST_SETTINGS) && !(p->Status&Status_Ground) &&
                (buttons&Buttons_A) && std::fabs(state->Speed.y+.4f)<.001f){
                float factor=host.targetRadius/100.0f;
                if(!std::isfinite(factor) || factor<.25f || factor>5)factor=1;
                hoverScale=factor;
                p->Position.x=stepStart.x+(p->Position.x-stepStart.x)*factor;
                p->Position.z=stepStart.z+(p->Position.z-stepStart.z)*factor;
            }
            {
                float dx=p->Position.x-stepStart.x,dy=p->Position.y-stepStart.y,dz=p->Position.z-stepStart.z;
                float speed=std::sqrt(stepSpeed.x*stepSpeed.x+stepSpeed.y*stepSpeed.y+stepSpeed.z*stepSpeed.z);
                float limit=16+speed*2*movementScale*hoverScale;
                bool covered=true;
                for (int axis=0;axis<3;axis++) {
                    float value=axis==0 ? p->Position.x : axis==1 ? p->Position.y : p->Position.z;
                    if (!std::isfinite(value) || std::fabs(value-worldFrame.center[axis])>worldFrame.radius-state->PhysicsData.RippleSize-.25f) covered=false;
                }
                if (!covered || dx*dx+dy*dy+dz*dz>limit*limit) {
                    p->Position=stepStart;p->Rotation=stepRotation;p->Status=stepStatus;state->Speed=stepSpeed;
                    nativeHeld=true;
                    if (covered) {
                        // An implausible solver displacement means stale contact
                        // work, not a real move. Invalidate that work before retry.
                        if (state->array_1x132) memset(state->array_1x132,0,132);
                        if (state->array_15x32) memset(state->array_15x32,0,15*32);
                        state->field_74=0;state->SurfaceFlags=state->SurfaceFlags_Old=0;
                    }
                    if (obj->Data2) {
                        NJS_VECTOR velocity=stepSpeed;
                        reinterpret_cast<void(__cdecl*)(EntityData1*,NJS_VECTOR*)>(0x43EC90)(p,&velocity);
                        reinterpret_cast<EntityData2*>(obj->Data2)->VelocityDirection=velocity;
                    }
                    break;
                }
            }
            if (p->Action==60 && oldAction!=60 && logFile) {
                fprintf(logFile,"Unexpected staging death: char=%u old=%u status=%x power=%x surface=%x pos=%f/%f/%f\n",host.character,oldAction,static_cast<unsigned short>(p->Status),static_cast<unsigned short>(state->Powerups),state->SurfaceFlags,p->Position.x,p->Position.y,p->Position.z);fflush(logFile);
            }
            TA_WallContact wall;
            float centerHeight=state->PhysicsData.YOff*.5f;
            float radius=state->PhysicsData.RippleSize; // player_parameter.rad
            if (radius>.1f && radius<100 && ta_world_wall(worldFrame,stepStart.x,stepStart.y+centerHeight,stepStart.z,
                p->Position.x,p->Position.y+centerHeight,p->Position.z,radius,wall,.3f) &&
                !(host.character==3 && p->Action==0x18)) {
                p->Position={wall.x,wall.y-centerHeight,wall.z};
                state->field_44={wall.nx,wall.ny,wall.nz};
                NJS_VECTOR speed=state->Speed;
                reinterpret_cast<void(__cdecl*)(EntityData1*,NJS_VECTOR*)>(0x43EC90)(p,&speed);
                float inward=speed.x*wall.nx+speed.y*wall.ny+speed.z*wall.nz;
                if (inward<0) {speed.x-=wall.nx*inward;speed.y-=wall.ny*inward;speed.z-=wall.nz*inward;}
                reinterpret_cast<void(__cdecl*)(EntityData1*,NJS_VECTOR*)>(0x43EC00)(p,&speed);
                state->Speed=speed;
            }
            ta_sonic_homing_contact(host,p,state,obj,stepStart,oldAction);
            TA_FloorContact floor;
            bool climbing=host.character==3 && p->Action==0x18;
            bool hasFloor=ta_world_floor_motion(worldFrame,stepStart.x,stepStart.y,stepStart.z,
                p->Position.x,p->Position.y,p->Position.z,state->PhysicsData.CollisionSize,wasGrounded,floor);
            if (!climbing && (p->Status&Status_Ground) &&
                !hasFloor) {
                // Native caches may still report the old floor after crossing
                // a ledge or updating a moving platform. Never stand on it.
                p->Status &= ~(Status_Ground|Status_OnColli);
                state->field_74=0;state->SurfaceFlags=state->SurfaceFlags_Old=0;
                if (state->array_1x132) memset(state->array_1x132,0,132);
                if (state->array_15x32) memset(state->array_15x32,0,15*32);
                if (state->Speed.y>0) state->Speed.y=0;
            }
            bool keepGround=wasGrounded && !(controller->PressedButtons&Buttons_A) &&
                ((p->Status&Status_Ground) || state->Speed.y<=.1f) && !climbing;
            if (host.character==1) keepGround=wasGrounded && oldAction!=8 && oldAction!=14 &&
                p->Action!=8 && p->Action!=14 && !(controller->PressedButtons&Buttons_A);
            if (hasFloor && !climbing &&
                (p->Position.y<floor.height-.001f ||
                 (keepGround &&
                  std::fabs(p->Position.y-floor.height)>.05f) ||
                 (!(p->Status&1) && p->Position.y<=floor.height+.05f && state->Speed.y<=0))) {
                p->Position.y=floor.height;
                if (!wasGrounded) audio.landing(p);
                state->SurfaceNormal={floor.nx,floor.ny,floor.nz};
                state->Speed.y=0;p->Status|=1;
                p->Rotation.x=static_cast<int>(std::atan2(floor.nz,floor.ny)*10430.37835f);
                p->Rotation.z=static_cast<int>(-std::atan2(floor.nx,floor.ny)*10430.37835f);
                state->_struct_a3.DistanceMax=floor.height;
                state->_struct_a3.ShadowRotationX=p->Rotation.x;
                state->_struct_a3.ShadowRotationY=p->Rotation.z;
            }
            if(host.character==5)ta_big_native_after(p);
        }
    }
    nativeVelocity={p->Position.x-before.x,p->Position.y-before.y,p->Position.z-before.z};
    if (advanceFrames>1) {nativeVelocity.x/=advanceFrames;nativeVelocity.y/=advanceFrames;nativeVelocity.z/=advanceFrames;}
    *controller=backup;*pointer=oldPointer;*polar=oldPolar;*heldButtons=oldHeld;*pressed=oldPressed;
    previousButtons=buttons;processedFrame=host.frame;
}
static void ta_hook_native_player() {
    auto obj=*reinterpret_cast<ObjectMaster**>(0x3B42E30);
    if (!obj || !obj->MainSub || obj->MainSub==ta_native_main) return;
    hookedPlayer=obj;originalPlayerMain=obj->MainSub;obj->MainSub=ta_native_main;
    nativeActive=false;
}
#endif
