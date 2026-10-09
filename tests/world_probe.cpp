#include "transport.h"
#include "collision_mirror.h"
#include <windows.h>
#include <cstring>
#include <cmath>
static TA_WorldFrame frame;
static TA_CollisionMirror mirror;
int main() {
    for (int i=0; i<100; i++) {
        if (ta_transport_read_world(&frame)) break;
        Sleep(10);
    }
    if (frame.count != 2 || frame.epoch != 7 || !mirror.build(frame)) return 1;
    if (mirror.table.COLCount != 1 || mirror.table.Col != mirror.collision) return 2;
    auto& a = mirror.models[0];
    if (a.nbPoint != 6 || a.meshsets->nbMesh != 2 || a.points[1].x != 10 || a.normals[0].y < .99f ||
        a.normals[3].z > -.99f) return 3;
    if (mirror.collision[0].Flags != ColFlags_Solid || mirror.objects[0].getbasicdxmodel() != &a) return 4;
    if (mirror.collision[0].Radius < 7.4f) return 5;
    frame.flags = TA_WORLD_TRUNCATED;
    if (mirror.build(frame) || mirror.table.COLCount!=1 || mirror.table.Col!=mirror.collision || mirror.models[0].nbPoint!=6) return 6;
    frame.flags = 0;
    // The expanded packet must convert every triangle without index/count wrap.
    auto source = frame.triangles[0];
    frame.count = TA_WORLD_CAPACITY;
    for (unsigned i = 0; i < frame.count; i++) frame.triangles[i] = source;
    if (!mirror.build(frame) || mirror.table.COLCount != TA_WORLD_CAPACITY/32) return 8;
    if (mirror.models[TA_WORLD_CAPACITY/32-1].nbPoint != 96 || mirror.models[TA_WORLD_CAPACITY/32-1].meshsets->nbMesh != 32 ||
        mirror.models[TA_WORLD_CAPACITY/32-1].meshsets->meshes[127] != 95 || mirror.models[TA_WORLD_CAPACITY/32-1].normals[95].y < .99f) return 9;
    frame.count = 2;
    memset(frame.triangles, 0, sizeof(frame.triangles));
    frame.triangles[0].flags = TA_SURFACE_SOLID;
    if (mirror.build(frame)) return 7; // Reject zero-area geometry.
    return 0;
}
