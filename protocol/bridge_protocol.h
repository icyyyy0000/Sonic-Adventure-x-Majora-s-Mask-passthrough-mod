#ifndef TA_BRIDGE_PROTOCOL_H
#define TA_BRIDGE_PROTOCOL_H
#ifdef MIPS
#include "PR/ultratypes.h"
typedef u32 uint32_t;
typedef s32 int32_t;
#else
#include <stdint.h>
#endif
// Cross-process ABI: all fields are 32-bit, little-endian; no process pointers.
// Character IDs: Link=0, Sonic=1, Tails=2, Knuckles=3, Amy=4, Big=5, Gamma=6.
#define TA_MAGIC 0x54414456u
#define TA_VERSION 4u
#ifdef TA_TEST_TRANSPORT
#define TA_MAPPING_NAME L"Local\\TerminaAdventure_Test_v4"
#define TA_MUTEX_NAME L"Local\\TerminaAdventure_Test_v4_lock"
#else
#define TA_MAPPING_NAME L"Local\\TerminaAdventure_v4"
#define TA_MUTEX_NAME L"Local\\TerminaAdventure_v4_lock"
#endif
#define TA_TIMEOUT_MS 1200u
#define TA_HOST_GAMEPLAY 1u
#define TA_HOST_NATIVE_PHYSICS 2u
#define TA_HOST_HOMING_TARGET 4u
#define TA_HOST_PAUSED 8u
#define TA_HOST_BIG_GRAPPLE 16u
#define TA_HOST_BIG_SLAM 32u
#define TA_HOST_SETTINGS 64u
#define TA_HOST_MUTE_CHARACTER 128u
#define TA_HOST_ALLOW_MUSIC 256u
#define TA_HOST_DISABLE_CLIMB 512u
#define TA_HOST_BIG_EMOTE 1024u
#define TA_HOST_BIG_ROD_ONLY 2048u
#define TA_HOST_GRAVITY_SHIFT 16u
#define TA_HOST_AMY_HEIGHT_SHIFT 20u
#define TA_HOST_PERCENT_MASK 15u
#define TA_HOST_SPEED_SHIFT 24u
#define TA_RENDER_BIG_WINDUP 32u
#define TA_RENDER_BIG_EMOTE 64u
#define TA_RENDER_BIG_GRAPPLE 4u
#define TA_RENDER_BIG_SLAM 8u
#define TA_RENDER_BIG_IMPACT 16u
#define TA_RENDER_GROUND_CURL 1u
#define TA_RENDER_TAILS_ROTOR 2u
// Tails' original procedural rotor angle occupies renderFlags' upper half.
#define TA_RENDER_ROTOR_SHIFT 16u
#define TA_GUEST_HAS_PLAYER 1u
#define TA_GUEST_MATCHING_CHARACTER 2u
#define TA_GUEST_WORLD_READY 4u
#define TA_GUEST_NATIVE_ACTIVE 8u
#pragma pack(push, 4)
typedef struct {
    uint32_t frame, scene, epoch, character, flags, buttons;
    int32_t stickX, stickY;
    float position[3], velocity[3], floorHeight, floorNormal[3];
    uint32_t grounded, yaw, cameraYaw;
    uint32_t targetId;
    float targetPosition[3], targetRadius;
} TA_HostFrame;
typedef struct {
    uint32_t frame, character, flags, action;
    float position[3], velocity[3], animationFrame;
    uint32_t yaw, status, animation;
    uint32_t scene, epoch, hostFrame, rotationX, rotationZ, actionIndex;
    float modelOffsetY;
    uint32_t previousActionIndex;
    float previousAnimationFrame, animationBlend;
    uint32_t hitSequence, hitTargetId;
    float nativeSpeed[3];
    uint32_t renderAnimation, renderFlags;
} TA_GuestFrame;
typedef struct {
    uint32_t magic, version, bytes, hostPid, guestPid, hostTime, guestTime, reserved;
    TA_HostFrame host;
    TA_GuestFrame guest;
} TA_Shared;
#pragma pack(pop)
#if defined(__cplusplus)
static_assert(sizeof(TA_HostFrame) == 104, "Host ABI drift");
static_assert(sizeof(TA_GuestFrame) == 124, "Guest ABI drift");
static_assert(sizeof(TA_Shared) == 260, "Shared ABI drift");
#endif
#endif
