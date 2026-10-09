"""CPU asset QA preview, not a screenshot of gameplay. Requires Pillow and numpy."""
import argparse
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from extract_models import PE, ROSTER, extract, extract_animation, textures

def rotate(axis, a):
    c, s = math.cos(a * math.tau / 65536), math.sin(a * math.tau / 65536)
    m = np.eye(4)
    x, y = [(1, 2), (2, 0), (0, 1)][axis]
    m[x,x] = m[y,y] = c
    m[x,y], m[y,x] = -s, s
    return m

def sample(keys, frame, angle=False):
    if not keys: return None
    idx = 0
    while idx + 1 < len(keys) and keys[idx + 1][0] <= frame: idx += 1
    a, b = keys[idx], keys[min(idx + 1, len(keys)-1)]
    weight = 0 if a[0] == b[0] else (frame-a[0])/(b[0]-a[0])
    delta = np.array(b[1:]) - np.array(a[1:])
    if angle: delta = (delta + 32768) % 65536 - 32768
    return np.array(a[1:]) + delta * weight

def render(pe, directory, prefix, action, width=360, height=480, pose=None):
    nodes, root = extract(pe, prefix, action)
    clip = extract_animation(pe, prefix, action, root, sum(n['animIndex'] >= 0 for n in nodes))
    texs = [(w,h,np.array(rgba).reshape(h,w,4)) for w,h,rgba in textures(directory/'system'/f'{prefix}.PVM')]
    mats, worldtris = [], []
    for n in nodes:
        pos, ang = np.array(n['pos']), np.array(n['ang'])
        if clip and n['animIndex'] >= 0:
            pk, rk = clip[1][n['animIndex']]
            pp, rr = sample(pk, 0), sample(rk, 0, True)
            if pp is not None: pos = pp
            if rr is not None: ang = rr
        if pose is not None: ang=pose(n['animIndex'],ang)
        m = np.eye(4)
        if not n['flags'] & 1 or (clip and pk): m[:3,3] = pos
        if pose is not None or not n['flags'] & 2 or (clip and rk):
            order = [1,0,2] if n['flags'] & 32 else [2,1,0]
            for axis in order: m = m @ rotate(axis, ang[axis])
        if not n['flags'] & 4: m = m @ np.diag([*n['scale'],1])
        m = (mats[n['parent']] if n['parent'] >= 0 else np.eye(4)) @ m
        mats.append(m)
        for points,color,uv,ti in n['triangles']:
            points = (m @ np.array([(*p,1) for p in points]).T).T[:,:3]
            worldtris.append((points,color,np.array(uv),ti))
    allpoints = np.concatenate([t[0] for t in worldtris])
    lo, hi = allpoints.min(axis=0), allpoints.max(axis=0)
    scale = min((width-35)/(hi[0]-lo[0]), (height-60)/(hi[1]-lo[1]))
    center = (lo+hi)/2
    rgb = np.full((height,width,3), (24,31,46), dtype=np.uint8)
    depth = np.full((height,width), -np.inf)
    for points,color,uv,ti in worldtris:
        xy = np.column_stack(((points[:,0]-center[0])*scale+width/2, height/2-(points[:,1]-center[1])*scale))
        x0,y0 = np.maximum(np.floor(xy.min(axis=0)).astype(int),0)
        x1,y1 = np.minimum(np.ceil(xy.max(axis=0)).astype(int),[width-1,height-1])
        if x0>x1 or y0>y1: continue
        ax,ay = xy[0]; bx,by = xy[1]; cx,cy = xy[2]
        den = (by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(den)<0.01: continue
        xx,yy = np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
        a=((by-cy)*(xx-cx)+(cx-bx)*(yy-cy))/den
        b=((cy-ay)*(xx-cx)+(ax-cx)*(yy-cy))/den
        c=1-a-b
        z=a*points[0,2]+b*points[1,2]+c*points[2,2]
        w,h,texture=texs[ti]
        u=((a*uv[0,0]+b*uv[1,0]+c*uv[2,0])/255*w).astype(int)%w
        v=((a*uv[0,1]+b*uv[1,1]+c*uv[2,1])/255*h).astype(int)%h
        pixels=texture[v,u]
        mask=(a>=0)&(b>=0)&(c>=0)&(z>depth[y0:y1+1,x0:x1+1])&(pixels[:,:,3]>=128)
        normal=np.cross(points[1]-points[0],points[2]-points[0])
        light=0.55+0.45*abs(np.dot(normal/ max(np.linalg.norm(normal),1e-9),[0.3,0.5,0.81]))
        shaded=np.clip(pixels[:,:,:3]*np.array(color[:3])/255*light,0,255).astype(np.uint8)
        rgb[y0:y1+1,x0:x1+1][mask]=shaded[mask]
        depth[y0:y1+1,x0:x1+1][mask]=z[mask]
    return Image.fromarray(rgb)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--sadx',required=True,type=Path)
    p.add_argument('--output',type=Path,default=Path('docs/asset-preview.png'))
    args=p.parse_args()
    pe=PE(args.sadx/'system/CHRMODELS_orig.dll')
    sheet=Image.new('RGB',(1080,1060),(17,23,34))
    draw=ImageDraw.Draw(sheet)
    for i,(name,prefix,actions) in enumerate(ROSTER):
        x,y=(i%3)*360,(i//3)*510+30
        sheet.paste(render(pe,args.sadx,prefix,actions[0]),(x,y))
        draw.text((x+12,y+480),name.title(),fill=(235,230,200))
    draw.text((12,8),'LOCAL SADX ASSET PREVIEW - not an in-game screenshot',fill=(230,230,230))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    sheet.save(args.output)
    print(args.output)
if __name__=='__main__': main()
