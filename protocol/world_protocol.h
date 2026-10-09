#ifndef TA_WORLD_PROTOCOL_H
#define TA_WORLD_PROTOCOL_H
#include "bridge_protocol.h"
#ifdef TA_TEST_TRANSPORT
#define TA_WORLD_MAPPING L"Local\\TerminaAdventure_Test_World_v4"
#else
#define TA_WORLD_MAPPING L"Local\\TerminaAdventure_World_v4"
#endif
#define TA_WORLD_CAPACITY 2048u
#define TA_WORLD_TRUNCATED 1u
#define TA_SURFACE_SOLID 1u
#define TA_SURFACE_DYNAMIC 2u
// Float positions are already converted to SADX coordinates. No game pointers.
typedef struct { uint32_t flags; float vertices[9]; } TA_Triangle;
typedef struct {
    uint32_t scene, epoch, revision, count, flags, reserved;
    float center[3], radius;
    TA_Triangle triangles[TA_WORLD_CAPACITY];
} TA_WorldFrame;
#ifdef __cplusplus
static_assert(sizeof(TA_Triangle) == 40, "Triangle ABI drift");
static_assert(sizeof(TA_WorldFrame) == 81960, "World ABI drift");
#endif
#endif
