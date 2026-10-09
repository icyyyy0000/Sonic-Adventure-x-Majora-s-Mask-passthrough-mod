#ifndef TA_WORLD_CONTACTS_H
#define TA_WORLD_CONTACTS_H
#include "world_protocol.h"
#include <cmath>
struct TA_FloorContact { float height, nx, ny, nz; };
struct TA_WallContact { float x,y,z,nx,ny,nz; };
static bool ta_world_wall(const TA_WorldFrame& world, float bx,float by,float bz,
                          float x,float y,float z,float radius,TA_WallContact& hit,float floorNormalY=.5f) {
    bool found=false;hit={x,y,z,0,0,0};
    for (unsigned i=0;i<world.count && i<TA_WORLD_CAPACITY;i++) {
        const auto& t=world.triangles[i];if (!(t.flags&TA_SURFACE_SOLID)) continue;
        const float* a=t.vertices;const float* b=a+3;const float* c=b+3;
        float ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2];
        float vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2];
        float nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;
        float length=std::sqrt(nx*nx+ny*ny+nz*nz);if (length<.00001f) continue;
        nx/=length;ny/=length;nz/=length;if (std::fabs(ny)>=floorNormalY) continue;
        float start=(bx-a[0])*nx+(by-a[1])*ny+(bz-a[2])*nz;
        if (start<0) {nx=-nx;ny=-ny;nz=-nz;start=-start;}
        float end=(hit.x-a[0])*nx+(hit.y-a[1])*ny+(hit.z-a[2])*nz;
        if (end>radius+.02f || end>start+.00001f) continue;
        float time=std::fabs(start-end)>.00001f ? (start-radius)/(start-end) : 0;if (time<0) time=0;if (time>1) time=1;
        float px=bx+(hit.x-bx)*time-nx*radius-a[0];
        float py=by+(hit.y-by)*time-ny*radius-a[1];
        float pz=bz+(hit.z-bz)*time-nz*radius-a[2];
        float uu=ux*ux+uy*uy+uz*uz,vv=vx*vx+vy*vy+vz*vz,uv=ux*vx+uy*vy+uz*vz;
        float pu=px*ux+py*uy+pz*uz,pv=px*vx+py*vy+pz*vz,den=uu*vv-uv*uv;
        if (std::fabs(den)<.00001f) continue;
        float u=(pu*vv-pv*uv)/den,v=(pv*uu-pu*uv)/den;
        if (u<-.00001f || v<-.00001f || u+v>1.00001f) continue;
        float push=radius>end ? radius-end : 0;
        hit.x+=nx*push;hit.y+=ny*push;hit.z+=nz*push;
        hit.nx=nx;hit.ny=ny;hit.nz=nz;found=true;
    }
    return found;
}
// Query the streamed geometry itself. Native contact work can retain a previous
// height when a model's points change in place; this repairs only penetrations.
static bool ta_world_floor(const TA_WorldFrame& world, float x, float z, float ceiling, TA_FloorContact& floor) {
    bool found=false;floor.height=-1000000;
    for (unsigned i=0;i<world.count && i<TA_WORLD_CAPACITY;i++) {
        const auto& t=world.triangles[i];if (!(t.flags&TA_SURFACE_SOLID)) continue;
        const float* a=t.vertices;const float* b=a+3;const float* c=b+3;
        float ux=b[0]-a[0],uz=b[2]-a[2],vx=c[0]-a[0],vz=c[2]-a[2];
        float den=ux*vz-uz*vx;
        if (std::fabs(den)<.00001f) continue;
        float u=((x-a[0])*vz-(z-a[2])*vx)/den;
        float v=(ux*(z-a[2])-uz*(x-a[0]))/den;
        if (u<-.00001f || v<-.00001f || u+v>1.00001f) continue;
        float uy=b[1]-a[1],vy=c[1]-a[1];
        float nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;
        float length=std::sqrt(nx*nx+ny*ny+nz*nz);
        if (length<.00001f || ny/length<.3f) continue;
        float height=a[1]+u*uy+v*vy;
        if (height>ceiling || height<=floor.height) continue;
        floor={height,nx/length,ny/length,nz/length};found=true;
    }
    return found;
}
// Endpoint-only height ceilings reject a fast uphill step when the ramp rises
// farther than the character's small stair height. Validate against the swept
// plane and slope gradient instead; overhead floors and distant drops stay out.
static bool ta_world_floor_motion(const TA_WorldFrame& world,float bx,float by,float bz,
                                  float x,float y,float z,float step,bool grounded,TA_FloorContact& floor) {
    bool found=false;floor.height=-1000000;
    float travel=std::sqrt((x-bx)*(x-bx)+(z-bz)*(z-bz));
    for (unsigned i=0;i<world.count && i<TA_WORLD_CAPACITY;i++) {
        const auto& t=world.triangles[i];if (!(t.flags&TA_SURFACE_SOLID)) continue;
        const float* a=t.vertices;const float* b=a+3;const float* c=b+3;
        float ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2];
        float vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2];
        float den=ux*vz-uz*vx;if (std::fabs(den)<.00001f) continue;
        float u=((x-a[0])*vz-(z-a[2])*vx)/den,v=(ux*(z-a[2])-uz*(x-a[0]))/den;
        if (u<-.00001f || v<-.00001f || u+v>1.00001f) continue;
        float nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;
        float length=std::sqrt(nx*nx+ny*ny+nz*nz);if (length<.00001f || ny/length<.3f) continue;
        float height=a[1]+u*uy+v*vy;
        float startHeight=a[1]-(nx*(bx-a[0])+nz*(bz-a[2]))/ny;
        bool crossed=by>=startHeight-.05f && y<=height+.05f;
        float reach=step+travel*std::sqrt(nx*nx+nz*nz)/ny+.05f;
        bool supported=grounded && by>=startHeight-step-.05f && std::fabs(height-by)<=reach;
        if ((!crossed && !supported) || height<=floor.height) continue;
        floor={height,nx/length,ny/length,nz/length};found=true;
    }
    return found;
}
#endif
