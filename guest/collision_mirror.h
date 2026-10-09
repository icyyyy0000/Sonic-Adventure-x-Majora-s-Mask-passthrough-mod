#ifndef TA_COLLISION_MIRROR_H
#define TA_COLLISION_MIRROR_H
#include <windows.h>
#include <string>
#include "SADXModInfo.h"
#include "world_protocol.h"
#include <cmath>
// Construct original Ninja basic collision geometry. Installation into the
// engine is deliberately separate: stage isolation must precede takeover.
struct TA_CollisionMirror {
    NJS_POINT3 points[TA_WORLD_CAPACITY * 6]{};
    NJS_VECTOR normals[TA_WORLD_CAPACITY * 6]{};
    Sint16 indices[TA_WORLD_CAPACITY * 8]{};
    NJS_MESHSET_SADX meshes[TA_WORLD_CAPACITY]{};
    NJS_MODEL_SADX models[TA_WORLD_CAPACITY]{};
    NJS_OBJECT objects[TA_WORLD_CAPACITY]{};
    COL collision[TA_WORLD_CAPACITY]{};
    LandTable table{};
    uint32_t revision{}, epoch{}, scene{};
    bool wallFacing=false;
    bool build(const TA_WorldFrame& frame,bool faceWalls=false) {
        if (!frame.count || frame.count > TA_WORLD_CAPACITY || (frame.flags & TA_WORLD_TRUNCATED)) return false;
        // This table remains installed outside the scoped player update. An
        // incomplete packet must not erase the last complete land underneath
        // the suspended task and invalidate the engine's contact work.
        table = {};
        unsigned count = 0, triangles = 0;
        // Preserve source face winding. Opposing coplanar wall faces repeatedly
        // cancel native movement. The swept guard handles the reverse approach.
        for (uint32_t t = 0; t < frame.count; t++) {
            const TA_Triangle& source = frame.triangles[t];
            if (!(source.flags & TA_SURFACE_SOLID)) continue;
            for (float v : source.vertices) if (!std::isfinite(v)) return false;
            NJS_POINT3 a{source.vertices[0],source.vertices[1],source.vertices[2]};
            NJS_POINT3 b{source.vertices[3],source.vertices[4],source.vertices[5]};
            NJS_POINT3 c{source.vertices[6],source.vertices[7],source.vertices[8]};
            NJS_VECTOR u{b.x-a.x,b.y-a.y,b.z-a.z}, v{c.x-a.x,c.y-a.y,c.z-a.z};
            NJS_VECTOR normal{u.y*v.z-u.z*v.y,u.z*v.x-u.x*v.z,u.x*v.y-u.y*v.x};
            float length = std::sqrt(normal.x*normal.x+normal.y*normal.y+normal.z*normal.z);
            if (length < 0.00001f) continue;
            normal.x /= length; normal.y /= length; normal.z /= length;
            // Knuckles' original climbing queries read front-facing land.
            // Orient one wall face toward the character; duplicating opposing
            // faces confuses the native solver. Floors retain their winding.
            if (faceWalls && std::fabs(normal.y)<.3f &&
                normal.x*(frame.center[0]-a.x)+normal.y*(frame.center[1]-a.y)+normal.z*(frame.center[2]-a.z)<0) {
                auto swap=b;b=c;c=swap;normal.x=-normal.x;normal.y=-normal.y;normal.z=-normal.z;
            }
            unsigned base = triangles * 3;
            points[base]=a;points[base+1]=b;points[base+2]=c;
            indices[triangles*4]=3;
            for (unsigned i=0;i<3;i++) {normals[base+i]=normal;indices[triangles*4+1+i]=(triangles%32)*3+i;}
            triangles++;
        }
        for (unsigned first = 0; first < triangles; first += 32) {
            unsigned num = triangles-first < 32 ? triangles-first : 32;
            unsigned base = first * 3;
            meshes[count] = {};
            meshes[count].type_matId = NJD_MESHSET_TRIMESH;
            meshes[count].nbMesh = num;
            meshes[count].meshes = &indices[first*4];
            models[count] = {};
            models[count].points = &points[base];
            models[count].normals = &normals[base];
            models[count].nbPoint = num * 3;
            models[count].meshsets = &meshes[count];
            models[count].nbMeshset = 1;
            NJS_POINT3 center{};
            for (unsigned i = 0; i < num*3; i++) { center.x+=points[base+i].x;center.y+=points[base+i].y;center.z+=points[base+i].z; }
            center.x/=num*3;center.y/=num*3;center.z/=num*3;
            float radius = 0;
            for (unsigned i = 0; i < num*3; i++) {
                NJS_POINT3 p = points[base+i];
                float d = (p.x-center.x)*(p.x-center.x)+(p.y-center.y)*(p.y-center.y)+(p.z-center.z)*(p.z-center.z);
                if (d > radius) radius = d;
            }
            radius = std::sqrt(radius) + 0.01f;
            models[count].center = center; models[count].r = radius;
            objects[count] = {};
            objects[count].evalflags = NJD_EVAL_UNIT_POS | NJD_EVAL_UNIT_ANG | NJD_EVAL_UNIT_SCL;
            objects[count].putbasicdxmodel(&models[count]);
            objects[count].scl[0] = objects[count].scl[1] = objects[count].scl[2] = 1;
            collision[count] = {};
            collision[count].Center = center; collision[count].Radius = radius;
            collision[count].Model = &objects[count];
            collision[count].Flags = ColFlags_Solid;
            count++;
        }
        table.COLCount = static_cast<int16_t>(count);
        table.Col = collision; table.ClippingDistance = frame.radius;
        scene = frame.scene; epoch = frame.epoch; revision = frame.revision;wallFacing=faceWalls;
        return count != 0;
    }
};
#endif
