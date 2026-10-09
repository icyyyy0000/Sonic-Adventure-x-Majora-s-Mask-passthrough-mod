#include "global.h"
#include "modding.h"
#include "world_protocol.h"
RECOMP_IMPORT(".", u32 ta_bridge_publish_world(void* frame, u32 words));
static TA_WorldFrame world;
static f32 queryRadius=1000.0f;
static void add_triangle(CollisionPoly* poly, Vec3s* vertices, Player* player, u32 flags) {
    // Exclusion flags occupy bits 13..15; the lower bits are a vertex index.
    if (COLPOLY_VIA_FLAG_TEST(poly->flags_vIA, COLPOLY_IGNORE_ENTITY)) return;
    u16 indices[] = { poly->flags_vIA & 0x1fff, poly->flags_vIB & 0x1fff, poly->vIC & 0x1fff };
    Vec3f low = { 1e6f, 1e6f, 1e6f }, high = { -1e6f, -1e6f, -1e6f };
    for (s32 i = 0; i < 3; i++) {
        Vec3s* v = &vertices[indices[i]];
        low.x = MIN(low.x, v->x); low.y = MIN(low.y, v->y); low.z = MIN(low.z, v->z);
        high.x = MAX(high.x, v->x); high.y = MAX(high.y, v->y); high.z = MAX(high.z, v->z);
    }
    Vec3f* p = &player->actor.world.pos;
    f32 r = queryRadius;
    if (high.x < p->x-r || low.x > p->x+r || high.y < p->y-r || low.y > p->y+r || high.z < p->z-r || low.z > p->z+r) return;
    if (world.count >= TA_WORLD_CAPACITY) { world.flags |= TA_WORLD_TRUNCATED; return; }
    TA_Triangle* t = &world.triangles[world.count++];
    t->flags = TA_SURFACE_SOLID | flags;
    for (s32 i = 0; i < 3; i++) {
        Vec3s* v = &vertices[indices[i]];
        t->vertices[i*3] = v->z / 2.8f;
        t->vertices[i*3+1] = v->y / 2.8f;
        t->vertices[i*3+2] = -v->x / 2.8f;
    }
}
void ta_export_world(Player* player, PlayState* play, u32 epoch, u32 frame) {
    // Dense rooms must never send a partial mesh which drops native ownership.
    // Re-query all static and dynamic geometry with a smaller complete window.
    if (world.scene!=(u32)play->sceneId || world.epoch!=epoch) queryRadius=1000.0f;
    else if (frame%60==0) queryRadius=MIN(1000.0f,queryRadius*1.25f);
    for (s32 attempt=0;attempt<7;attempt++) {
    world.count = world.flags = 0;
    world.scene = play->sceneId; world.epoch = epoch; world.revision = frame;
    world.center[0] = player->actor.world.pos.z / 2.8f;
    world.center[1] = player->actor.world.pos.y / 2.8f;
    world.center[2] = -player->actor.world.pos.x / 2.8f;
    world.radius = queryRadius / 2.8f;
    // Dynamic vertices are the transformed world-space list maintained by Zelda.
    DynaCollisionContext* dyna = &play->colCtx.dyna;
    for (s32 i = 0; i < BG_ACTOR_MAX; i++) {
        BgActor* a = &dyna->bgActors[i];
        if (!(dyna->bgActorFlags[i] & BGACTOR_IN_USE) ||
            (dyna->bgActorFlags[i] & BGACTOR_COLLISION_DISABLED) || !a->colHeader || !dyna->polyList || !dyna->vtxList) continue;
        for (s32 j = 0; j < a->colHeader->numPolygons; j++)
            add_triangle(&dyna->polyList[a->dynaLookup.polyStartIndex+j], dyna->vtxList, player, TA_SURFACE_DYNAMIC);
    }
    CollisionHeader* header = play->colCtx.colHeader;
    if (header && header->vtxList && header->polyList)
        for (s32 i = 0; i < header->numPolygons; i++) add_triangle(&header->polyList[i], header->vtxList, player, 0);
    if (!(world.flags&TA_WORLD_TRUNCATED)) break;
    f32 smaller=MAX(40.0f,queryRadius*.65f);
    if (smaller==queryRadius) break;
    queryRadius=smaller;
    }
    ta_bridge_publish_world(&world, sizeof(world) / 4);
}
