// Native companion: observe the engine and request full character swaps through
// the user's installed Character Select mod. World takeover is a separate step.
#include <windows.h>
#include <string>
#include "SADXModInfo.h"
#include "transport.h"
#include "collision_mirror.h"
#include "character_select.h"
#include "owned_input.h"
#include <stdio.h>
// Addresses from the official SADXVariables.h, for the supported converted 2004 EXE.
static EntityData1** const players = reinterpret_cast<EntityData1**>(0x3B42E10);
static CharObj2** const physics = reinterpret_cast<CharObj2**>(0x3B3CDF0);
static unsigned frameNumber;
static TA_WorldFrame worldFrame;
static TA_CollisionMirror mirrorBuffers[2];
static unsigned mirrorSlot;
static TA_CollisionMirror& ta_current_mirror() {return mirrorBuffers[mirrorSlot];}
static bool ta_refresh_mirror(const TA_WorldFrame& frame) {
    auto& current=ta_current_mirror();
    bool faceWalls=players[0] && players[0]->CharID==Characters_Knuckles;
    if (current.epoch==frame.epoch && current.scene==frame.scene && current.revision==frame.revision && current.wallFacing==faceWalls)
        return current.table.COLCount>0;
    // Collision work outside the player stores model pointers. Give a new scene
    // distinct model addresses; do not overwrite the previous scene in place.
    if (current.epoch!=frame.epoch || current.scene!=frame.scene) mirrorSlot^=1;
    return ta_current_mirror().build(frame,faceWalls);
}
static bool worldReady;
static LandTable* originalStageTable;
static short originalMobileCount;
static bool autoMatch = true, showHud = true, muteStageMusic=true;
static unsigned requestCooldown, lastCharacter = 0xffffffffu;
static unsigned requestedCharacter;
static FILE* logFile;
static int* const heldButtons = reinterpret_cast<int*>(0x3B0E3A8);
static short* const levelId = reinterpret_cast<short*>(0x3B22DCC);
static short* const cutsceneMode = reinterpret_cast<short*>(0x3B22E1C);
static GameModes* const gameMode = reinterpret_cast<GameModes*>(0x3ABDC7C);
static auto const paused = reinterpret_cast<bool(__cdecl*)()>(0x414D70);
static auto const fontSize = reinterpret_cast<void(__cdecl*)(unsigned short)>(0x7808C0);
static auto const fontColor = reinterpret_cast<void(__cdecl*)(int)>(0x7808E0);
static auto const debugText = reinterpret_cast<void(__cdecl*)(int, const char*)>(0x7808F0);
static const char* names[] = {"Link", "Sonic", "Tails", "Knuckles", "Amy", "Big", "E-102 Gamma"};
static uint32_t character_id(char id) {
    switch (id) {
    case Characters_Sonic: return 1;
    case Characters_Tails: return 2;
    case Characters_Knuckles: return 3;
    case Characters_Amy: return 4;
    case Characters_Big: return 5;
    case Characters_Gamma: return 6;
    default: return 0;
    }
}
static TA_HostFrame cachedHost;
static TA_WorldFrame cachedWorld;
static DWORD cachedHostAt, cachedWorldAt;
static bool haveHost, haveWorld;
static bool ta_read_host(TA_HostFrame* output) {
    TA_HostFrame fresh{};
    DWORD now=GetTickCount();
    if (ta_transport_read_host(&fresh)) {
        // A repeated frame is not a new heartbeat for our cache.
        if (!haveHost || fresh.frame!=cachedHost.frame || fresh.epoch!=cachedHost.epoch) cachedHostAt=now;
        cachedHost=fresh;haveHost=true;
    }
    if (!haveHost || DWORD(now-cachedHostAt)>150) return false;
    *output=cachedHost;return true;
}
static bool ta_read_world(TA_WorldFrame* output) {
    DWORD now=GetTickCount();
    if (ta_transport_read_world(&cachedWorld)) {cachedWorldAt=now;haveWorld=true;}
    if (!haveWorld || !haveHost || DWORD(now-cachedWorldAt)>150 ||
        cachedWorld.epoch!=cachedHost.epoch || cachedWorld.scene!=cachedHost.scene) return false;
    *output=cachedWorld;return true;
}
#include "native_player.h"
#include "stage_guard.h"
static unsigned native_action_index(CharObj2* state,unsigned character,int index) {
    if (!state || !state->AnimationThing.AnimData || index<0 || index>255) return 0xffff;
    NJS_ACTION* action=state->AnimationThing.AnimData[index].Animation;
    const char* exports[]={"","___SONIC_ACTIONS","___MILES_ACTIONS","___KNUCKLES_ACTIONS","___AMY_ACTIONS","___BIG_ACTIONS","___E102_ACTIONS"};
    HMODULE modelDll=GetModuleHandleA("CHRMODELS_orig.dll");
    if (!modelDll) modelDll=GetModuleHandleA("CHRMODELS.dll");
    auto list=reinterpret_cast<NJS_ACTION**>(modelDll && character<7 ? GetProcAddress(modelDll,exports[character]) : nullptr);
    unsigned counts[]={0,149,114,90,80,90,78};
    if (list) for (unsigned i=0;i<counts[character];i++) if (list[i]==action) return i;
    return 0xffff;
}
extern "C" {
// Uses only the longstanding OnFrame/OnExit ABI; no newer HelperFunctions.
__declspec(dllexport) ModInfo SADXModInfo = { 16 };
__declspec(dllexport) void __cdecl Init(const char* path, const HelperFunctions&) {
    std::string config = std::string(path) + "\\config.ini";
    autoMatch = GetPrivateProfileIntA("Bridge", "AutoMatchCharacter", 1, config.c_str()) != 0;
    showHud = GetPrivateProfileIntA("Bridge", "ShowHUD", 1, config.c_str()) != 0;
    nativeEnabled = GetPrivateProfileIntA("Bridge", "NativePhysics", 1, config.c_str()) != 0;
    nativeCharacterSounds = GetPrivateProfileIntA("Bridge", "CharacterSounds", 1, config.c_str()) != 0;
    muteStageMusic = GetPrivateProfileIntA("Bridge", "MuteStageMusic", 1, config.c_str()) != 0;
    std::string logPath = std::string(path) + "\\bridge.log";
    logFile = fopen(logPath.c_str(), "w");
    if (logFile) { fputs("Termina Adventure native companion 0.1.17 loaded. Original task physics with scoped Zelda collision enabled.\n", logFile); fflush(logFile); }
}
__declspec(dllexport) void __cdecl OnInput() {
    TA_HostFrame host{};
    bool connected=ta_read_host(&host)!=0;
    if (!nativeEnabled || !((connected && (host.flags&TA_HOST_NATIVE_PHYSICS || !host.character)) ||
        (!connected && nativeSession))) return;
    auto pointers=reinterpret_cast<ControllerData**>(0x3B0E77C);
    auto controllers=reinterpret_cast<ControllerData*>(0x3B0E7F0);
    for (unsigned i=0;i<8;i++) {
        if (pointers[i]) ta_clear_owned_pad(*pointers[i]);
        ta_clear_owned_pad(controllers[i]);
        heldButtons[i]=0;reinterpret_cast<int*>(0x3B0E354)[i]=0;
    }
}
__declspec(dllexport) void __cdecl OnControl() {
    TA_HostFrame host{};
    bool connected=ta_read_host(&host)!=0;
    if (nativeEnabled && ((connected && host.character && (host.flags & TA_HOST_NATIVE_PHYSICS)) ||
        (!connected && nativeSession))) {
        // Physical gamepad input reaches both games. Keep it from triggering
        // Character Select while Zelda owns selection and native task input.
        auto pad=reinterpret_cast<ControllerData*>(0x3B0E7F0);
        auto pressed=reinterpret_cast<int*>(0x3B0E354);
        ta_filter_owned_start(*pad,heldButtons[0],*pressed);
        heldButtons[0]=0;
    }
    if (connected && requestedCharacter!=host.character) {requestedCharacter=host.character;requestCooldown=0;}
    if (requestCooldown) { requestCooldown--; return; }
    if (!autoMatch || !connected || !(host.flags & TA_HOST_GAMEPLAY) ||
        !host.character || host.character > 6 || !players[0] || !physics[0] ||
        *gameMode == GameModes_Menu || *cutsceneMode || paused() ||
        *levelId == LevelIDs_SkyChase1 || *levelId == LevelIDs_SkyChase2 ||
        !GetModuleHandleA("SADXCharSel.dll")) return;
    if (character_id(players[0]->CharID) != host.character) {
        // Character Select destroys CharObj2 before initializing the new task.
        // Tails checks inherited Hurt before that initialization and dereferences
        // the absent physics object. Never transfer staging contact damage.
        players[0]->Status&=~(Status_Hurt|Status_OnColli);
        physics[0]->Powerups&=~0xc000;physics[0]->SurfaceFlags&=~0x10000;
        heldButtons[0] = static_cast<int>(ta_selection_buttons(host.character));
        requestCooldown = 6;
        if (logFile) { fprintf(logFile, "Requesting original %s task via Character Select.\n", names[host.character]); fflush(logFile); }
    }
}
__declspec(dllexport) void __cdecl OnFrame() {
    // Run before Character Select. Leave only the requested selection chord
    // until its OnFrame; the next OnInput clears it before the engine reads it.
    if(players[0] && physics[0]) {
        TA_HostFrame selection{};
        if(ta_read_host(&selection) && selection.character && character_id(players[0]->CharID)!=selection.character){
            players[0]->Status&=~(Status_Hurt|Status_OnColli);
            physics[0]->Powerups&=~0xc000;physics[0]->SurfaceFlags&=~0x10000;
        }
    }
    ta_hook_native_player();
    TA_HostFrame host{};
    bool connected = ta_read_host(&host) != 0;
    if (connected && (!host.character || (host.flags&TA_HOST_MUTE_CHARACTER))) {
        ta_stop_owned_audio();
        // Idle-chatter/voice mods can start streams outside the owned task.
        // Only SADX's voice stream is stopped; Zelda audio is in another process.
        reinterpret_cast<void(__cdecl*)()>(0x425730)();
    }
    // Music uses its own stream. Stop only that stream, leaving effect/voice
    // banks and the user's SADX master/effect volumes untouched.
    bool muteMusic=connected && (host.flags&TA_HOST_SETTINGS) ? !(host.flags&TA_HOST_ALLOW_MUSIC) : muteStageMusic;
    static bool wasMusicMuted;
    if(wasMusicMuted && !muteMusic && connected)reinterpret_cast<void(__cdecl*)(int)>(0x425690)(MusicIDs_StationSquare);
    wasMusicMuted=muteMusic;
    if (muteMusic && (connected || nativeSession) && *reinterpret_cast<int*>(0x3ABDFA0))
        reinterpret_cast<void(__cdecl*)()>(0x4256B0)();
    if (players[0] && physics[0]) {
        unsigned actual = character_id(players[0]->CharID);
        if (actual != lastCharacter) {
            if (logFile) { fprintf(logFile, "Original SADX player loaded = %s (connected=%u)\n", names[actual], connected ? 1u : 0u); fflush(logFile); }
            lastCharacter = actual;
        }
    }
    if (showHud && players[0] && physics[0]) {
        char text[160];
        unsigned actual = character_id(players[0]->CharID);
        fontSize(12); fontColor(0xffffff80);
        snprintf(text, sizeof(text), "Termina: SADX %s | Zelda %s", names[actual], connected && host.character <= 6 ? names[host.character] : "not connected");
        debugText(0x00010001, text);
        debugText(0x00010002, nativeActive ? "Original physics | Zelda collision" : "Character matching | awaiting physics ownership");
        fontColor(0xffbfbfbf); fontSize(8);
    }
    if (!connected) {
        if (nativeSession) ta_guard_stage_tasks();
        if (originalStageTable && !(nativeSession)) {
            *reinterpret_cast<LandTable**>(0x3B2F718)=originalStageTable;originalStageTable=nullptr;
            *reinterpret_cast<short*>(0x3B2D510)=originalMobileCount;
            reinterpret_cast<void(__cdecl*)()>(0x43B580)();
        }
        return;
    }
    TA_GuestFrame guest{};
    guest.frame = ++frameNumber;
    worldReady = false;
    if (ta_read_world(&worldFrame)) {
        bool built=ta_refresh_mirror(worldFrame);
        worldReady = built && ta_current_mirror().table.COLCount > 0 && !(worldFrame.flags & TA_WORLD_TRUNCATED);
    }
    // The original solver also prepares private collision caches outside the
    // player task. Keep the mirror installed for that whole engine frame.
    if (nativeEnabled && (host.flags & TA_HOST_NATIVE_PHYSICS) && worldReady) {
        auto current=reinterpret_cast<LandTable**>(0x3B2F718);
        if (!originalStageTable) {originalStageTable=*current;originalMobileCount=*reinterpret_cast<short*>(0x3B2D510);}
        *current=&ta_current_mirror().table;
        *reinterpret_cast<short*>(0x3B2D510)=0;
        reinterpret_cast<void(__cdecl*)()>(0x43B580)();
        ta_guard_stage_tasks();
    } else if (originalStageTable && !(nativeSession && host.character && (host.flags&TA_HOST_NATIVE_PHYSICS))) {
        *reinterpret_cast<LandTable**>(0x3B2F718)=originalStageTable;originalStageTable=nullptr;
        *reinterpret_cast<short*>(0x3B2D510)=originalMobileCount;
        reinterpret_cast<void(__cdecl*)()>(0x43B580)();
    } else if (originalStageTable && nativeSession && host.character) {
        ta_guard_stage_tasks();
    }
    if (worldReady) guest.flags |= TA_GUEST_WORLD_READY;
    if (nativeActive && nativeSession) guest.flags |= TA_GUEST_NATIVE_ACTIVE;
    guest.scene=nativeScene;guest.epoch=nativeEpoch;guest.hostFrame=processedFrame;
    EntityData1* player = players[0];
    CharObj2* state = physics[0];
    if (player && state) {
        guest.character = character_id(player->CharID);
        guest.flags |= TA_GUEST_HAS_PLAYER;
        if (guest.character == host.character) guest.flags |= TA_GUEST_MATCHING_CHARACTER;
        guest.action = static_cast<unsigned char>(player->Action);
        guest.position[0] = player->Position.x;
        guest.position[1] = player->Position.y;
        guest.position[2] = player->Position.z;
        guest.velocity[0] = state->Speed.x;
        guest.velocity[1] = state->Speed.y;
        guest.velocity[2] = state->Speed.z;
        guest.yaw = player->Rotation.y;
        guest.status = static_cast<uint16_t>(player->Status);
        guest.animationFrame = state->AnimationThing.Frame;
        guest.animation = state->AnimationThing.Index;
        guest.nativeSpeed[0]=state->Speed.x;guest.nativeSpeed[1]=state->Speed.y;guest.nativeSpeed[2]=state->Speed.z;
        guest.hitSequence=sonicHitSequence;guest.hitTargetId=sonicHitTarget;
        guest.rotationX=player->Rotation.x;guest.rotationZ=player->Rotation.z;
        // Calibrated against extracted idle shoe vertices: the body anchor
        // needs the full centre height for the converted model hierarchy.
        guest.modelOffsetY=state->PhysicsData.YOff;
        static float stableAnimationFrame;
        static unsigned stableCharacter;
        auto& anim=state->AnimationThing;
        guest.animationBlend=1.0f;
        guest.previousActionIndex=0xffff;
        int displayIndex=guest.character==1 ? ta_sonic_render_index(state,player) : anim.State==2 ? anim.LastIndex : anim.Index;
        guest.renderAnimation=displayIndex;
        guest.renderFlags=guest.character==1 && (anim.State==2 ? anim.LastIndex : anim.Index)==14 && (player->Status&3) ? TA_RENDER_GROUND_CURL : 0;
        guest.actionIndex=native_action_index(state,guest.character,displayIndex);
        if(guest.character==3 && knucklesClinging){guest.action=0x18;guest.actionIndex=native_action_index(state,3,0x34);guest.animationFrame=knucklesClimbFrame;guest.previousActionIndex=0xffff;guest.animationBlend=1;}
        if(guest.character==5){guest.renderFlags=ta_big_render_flags();guest.hitSequence=bigImpactSequence;guest.hitTargetId=bigNativeCommand;}
        if (guest.character==2 && displayIndex>=37 && displayIndex<=41) {
            guest.renderFlags=TA_RENDER_TAILS_ROTOR |
                (tailsRotorAngle<<TA_RENDER_ROTOR_SHIFT);
        }
        // The alternating blur mesh is designed for SADX's textured 60 Hz draw.
        // At Zelda's 20 Hz snapshots it aliases into silhouette flicker. Keep the
        // original curled motion as the stable visual; native action is untouched.
        if (guest.character==1 && displayIndex==32)
            guest.actionIndex=native_action_index(state,1,14);
        if (anim.State==2) {
            guest.previousActionIndex=native_action_index(state,guest.character,anim.LastIndex2);
            guest.previousAnimationFrame=stableCharacter==guest.character ? stableAnimationFrame : 0;
            guest.animationBlend=anim.Frame<0 ? 0 : anim.Frame>1 ? 1 : anim.Frame;
            guest.animationFrame=0; // During state 2 Frame is a blend factor, not a motion frame.
        } else {stableCharacter=guest.character;stableAnimationFrame=anim.Frame;}
        if (nativeActive) {guest.velocity[0]=nativeVelocity.x;guest.velocity[1]=nativeVelocity.y;guest.velocity[2]=nativeVelocity.z;}
    }
    ta_transport_write_guest(&guest);
}
__declspec(dllexport) void __cdecl OnExit() {
    if (originalStageTable) {*reinterpret_cast<LandTable**>(0x3B2F718)=originalStageTable;originalStageTable=nullptr;}
    ta_transport_close(); if (logFile) fclose(logFile); logFile = nullptr;
}
}
