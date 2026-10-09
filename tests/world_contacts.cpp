#include "world_contacts.h"
#include <cstdio>
static TA_WorldFrame world;
int main() {
    world.count=1;world.triangles[0].flags=TA_SURFACE_SOLID;
    float v[]={-100,-20,-100,100,20,100,100,20,-100};
    for (int i=0;i<9;i++) world.triangles[0].vertices[i]=v[i];
    TA_FloorContact floor;
    if (!ta_world_floor(world,50,0,100,floor) || std::fabs(floor.height-10)>.001 || floor.ny<.98f) return 1;
    if (ta_world_floor(world,50,0,5,floor)) return 2; // overhead floor must not capture a fall
    if (ta_world_floor(world,500,0,100,floor)) return 3; // real gaps remain gaps
    world.triangles[0].flags=0;
    if (ta_world_floor(world,50,0,100,floor)) return 4;
    world.triangles[0].flags=TA_SURFACE_SOLID;
    float wallVerts[]={10,-100,-100,10,100,100,10,100,-100};
    for (int i=0;i<9;i++) world.triangles[0].vertices[i]=wallVerts[i];
    TA_WallContact wall;
    if (!ta_world_wall(world,0,0,0,30,0,-5,2,wall) || std::fabs(wall.x-8)>.001 || wall.z!=-5) return 5;
    if (ta_world_wall(world,8,0,0,0,0,0,2,wall)) return 6; // movement away is free
    if (ta_world_wall(world,0,500,0,30,500,0,2,wall)) return 7; // above a wall is free
    if (!ta_world_wall(world,8.2f,0,0,9,0,-5,2,wall) || std::fabs(wall.x-8)>.001 || wall.z!=-5) return 8;
    if (ta_world_wall(world,8.2f,0,0,7,0,0,2,wall)) return 9;
    float grades[]={.8f,1.5f,2.5f};
    for (float grade:grades) {
        float ramp[]={-100,-100*grade,-100,100,100*grade,100,100,100*grade,-100};
        for (int i=0;i<9;i++) world.triangles[0].vertices[i]=ramp[i];
        if (ta_world_floor(world,10,0,3,floor)) return 10; // reproduces old uphill ceiling failure
        if (!ta_world_floor_motion(world,0,0,0,10,0,0,3,true,floor) || std::fabs(floor.height-10*grade)>.001f) return 11;
        if (!ta_world_floor_motion(world,10,10*grade,0,0,10*grade,0,3,true,floor) || std::fabs(floor.height)>.001f) return 12;
        if (ta_world_wall(world,0,2,0,10,2,0,2,wall,.3f)) return 13; // walkable ramp must not also push as wall
        if (!ta_world_floor_motion(world,0,3,0,10,0,0,3,false,floor)) return 14; // landing onto uphill terrain
    }
    float overhead[]={-100,30,-100,100,30,100,100,30,-100};
    for (int i=0;i<9;i++) world.triangles[0].vertices[i]=overhead[i];
    if (ta_world_floor_motion(world,0,0,0,10,0,0,3,true,floor)) return 15;
    if (ta_world_floor_motion(world,0,0,0,10,40,0,3,false,floor)) return 16; // rising through underside isn't landing
    if (ta_world_floor_motion(world,0,60,0,10,60,0,3,true,floor)) return 17; // distant lower platform isn't a stair
    if (ta_world_floor_motion(world,500,40,0,510,0,0,3,false,floor)) return 18; // preserve gaps
    puts("PASS: floor slopes/gaps and swept wall contact, sliding, release and bounds.");
    return 0;
}
