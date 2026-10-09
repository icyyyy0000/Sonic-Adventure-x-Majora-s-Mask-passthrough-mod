"""Extract original per-action model variants and motions from local SADX data."""
import argparse,json,copy
from pathlib import Path
from extract_models import PE,extract,extract_animation,textures,cfloat,model_triangles

def flying_tail_geometry(pe,nodes):
    """Tails_Display selects separate rotor objects 16/17 during flight.

    Keep the canonical 68-bone motion layout; replace the two compatible tail
    subtrees' static geometry with the original rotor geometry.
    """
    nodes=copy.deepcopy(nodes);objects=pe.exports['___MILES_OBJECTS'];roots=[]
    for normal,rotor in [(14,16),(15,17)]:
        original=pe.pointer(objects+normal*4)
        base=next(i for i,n in enumerate(nodes) if n['source']==original)
        branch=[]
        def walk(addr,parent=-1,follow=True):
            while addr:
                row=pe.read(addr,'IIfffiiifffII');idx=len(branch);branch.append((parent,row))
                if row[-2] and not row[0]&16:walk(row[-2],idx)
                addr=row[-1] if follow else 0
        walk(pe.pointer(objects+rotor*4),follow=False)
        end=base+1
        while end<len(nodes) and nodes[end]['parent']>=base:end+=1
        assert end-base==len(branch),(normal,'Incompatible rotor topology')
        for offset,(parent,row) in enumerate(branch):
            node=nodes[base+offset]
            if offset:assert node['parent']==base+parent
            node['triangles']=model_triangles(pe,row[1]) if row[1] and not row[0]&8 else []
            if offset:node['pos']=list(row[2:5]);node['ang']=list(row[5:8]);node['scale']=list(row[8:11])
        nodes[base]['flags']&=~2;roots.append(base)
    assert roots==[59,63],roots
    return nodes

def emit_nodes(lines,char,texture_prefix,nodes,texs):
    for n, node in enumerate(nodes):
        tris = node['triangles']
        if not tris:
            continue
        lines.append(f'static Vtx {char}_v{n}[] = {{')
        for points, color, texcoords, ti in tris:
            w, h, _ = texs[ti]
            for xyz, uv in zip(points, texcoords):
                # Quantize local coordinates at 1/256 SADX unit.
                coords = [round(x * 256) for x in xyz]
                if any(abs(v) > 32767 for v in coords):
                    raise ValueError('Model local coordinate outside N64 vertex range')
                st = [round(uv[0] / 255 * w * 32), round(uv[1] / 255 * h * 32)]
                lines.append('    {{{%d,%d,%d},0,{%d,%d},{%d,%d,%d,%d}}},' % (*coords, *st, *color))
        lines.append('};')
        lines.append(f'static Gfx {char}_dl{n}[] = {{')
        start = 0
        lastTexture = -1
        while start < len(tris):
            ti = tris[start][3]
            if ti != lastTexture:
                w, h, _ = texs[ti]
                lines.append(f'    gsDPLoadTextureBlock({texture_prefix}_tex{ti}, G_IM_FMT_RGBA, G_IM_SIZ_16b, {w}, {h}, 0, G_TX_WRAP, G_TX_WRAP, {w.bit_length()-1}, {h.bit_length()-1}, G_TX_NOLOD, G_TX_NOLOD),')
                lastTexture = ti
            batch = 1
            while batch < 10 and start + batch < len(tris) and tris[start + batch][3] == ti:
                batch += 1
            lines.append(f'    gsSPVertex({char}_v{n} + {start * 3}, {batch * 3}, 0),')
            for t in range(batch):
                lines.append(f'    gsSP1Triangle({t * 3}, {t * 3 + 1}, {t * 3 + 2}, 0),')
            start += batch
        lines += ['    gsSPEndDisplayList(),', '};']
    lines.append(f'static TA_ModelNode {char}_nodes[] = {{')
    for n, node in enumerate(nodes):
        dl = f'{char}_dl{n}' if node['triangles'] else 'NULL'
        pos = ','.join(cfloat(x) for x in node['pos'])
        scale = ','.join(cfloat(x) for x in node['scale'])
        ang = ','.join(str((x + 32768) % 65536 - 32768) for x in node['ang'])
        lines.append(f'    {{{node["parent"]},{node["flags"]},{{{pos}}},{{{ang}}},{{{scale}}},{dl},{node["animIndex"]}}},')
    lines.append('};')

def emit_tracks(lines,char,ci,clip):
    frames, bones = clip
    for bi, (posKeys, rotKeys, scaleKeys) in enumerate(bones):
        if posKeys:
            lines.append(f'static TA_PosKey {char}_p{ci}_{bi}[] = {{')
            lines += ['    {%d,{%s}},' % (key[0], ','.join(cfloat(v) for v in key[1:])) for key in posKeys]
            lines.append('};')
        if rotKeys:
            lines.append(f'static TA_RotKey {char}_r{ci}_{bi}[] = {{')
            lines += ['    {%d,{%s}},' % (key[0], ','.join(str((v+32768)%65536-32768) for v in key[1:])) for key in rotKeys]
            lines.append('};')
        if scaleKeys:
            lines.append(f'static TA_PosKey {char}_s{ci}_{bi}[] = {{')
            lines += ['    {%d,{%s}},' % (key[0], ','.join(cfloat(v) for v in key[1:])) for key in scaleKeys]
            lines.append('};')
    lines.append(f'static TA_BoneTrack {char}_tracks{ci}[] = {{')
    for bi, (posKeys, rotKeys, scaleKeys) in enumerate(bones):
        pp = f'{char}_p{ci}_{bi}' if posKeys else 'NULL'
        rp = f'{char}_r{ci}_{bi}' if rotKeys else 'NULL'
        sp = f'{char}_s{ci}_{bi}' if scaleKeys else 'NULL'
        lines.append(f'    {{{len(posKeys)},{len(rotKeys)},{pp},{rp},{len(scaleKeys)},{sp}}},')
    lines.append('};')

def main():
    p=argparse.ArgumentParser();p.add_argument('--sadx',type=Path,required=True);args=p.parse_args()
    pe=PE(args.sadx/'system/CHRMODELS_orig.dll');out=Path('src/generated');report={}
    roster=[('sonic','SONIC',149),('tails','MILES',114),('knuckles','KNUCKLES',90),('amy','AMY',80),('big','BIG',90),('gamma','E102',78)]
    for char,prefix,count in roster:
        texs=textures(args.sadx/'system'/f'{prefix}.PVM')
        lines=['/* LOCAL GAME ASSETS: do not redistribute. */','#include "render/character_model.h"']
        for ti,(w,h,rgba) in enumerate(texs):
            lines.append(f'static u16 {char}_tex{ti}[] __attribute__((aligned(8))) = {{')
            for y in range(h):
                values=[(r>>3)<<11|(g>>3)<<6|(b>>3)<<1|int(a>=128) for r,g,b,a in rgba[y*w:(y+1)*w]]
                lines.append('    '+','.join(f'0x{x:04x}' for x in values)+',')
            lines.append('};')
        variants={};entries=[];supported=0;skipped=[]
        for actionIndex in range(count):
            # The roster does not include Metal Sonic or Super Sonic.
            if char=='sonic' and (actionIndex==0 or actionIndex>=130):entries.append(None);continue
            try:
                nodes,root=extract(pe,prefix,actionIndex)
                if len(nodes)>128:raise ValueError('Node count exceeds renderer capacity')
                bones=sum(n['animIndex']>=0 for n in nodes)
                clip=extract_animation(pe,prefix,actionIndex,root,bones,include_scale=True)
                if not clip:raise ValueError('Unsupported motion channels')
                rotor=char=='tails' and actionIndex in range(37,42)
                variantKey=(root,rotor)
                if rotor:nodes=flying_tail_geometry(pe,nodes)
                if variantKey not in variants:
                    variant=f'{char}_variant{len(variants)}'
                    emit_nodes(lines,variant,char,nodes,texs)
                    variants[variantKey]=(variant,len(nodes))
                variant,nodeCount=variants[variantKey]
                emit_tracks(lines,char,actionIndex,clip)
                entries.append((variant,nodeCount,clip[0],actionIndex));supported+=1
            except (ValueError,IndexError,KeyError) as error:
                entries.append(None);skipped.append({'action':actionIndex,'reason':str(error)})
        lines.append(f'TA_NativeAction ta_native_{char}[{count}] = {{')
        for e in entries:
            lines.append(f'    {{{e[1]},{e[0]}_nodes,{{{e[2]},{char}_tracks{e[3]}}}}},' if e else '    {0,NULL,{0,NULL}},')
        lines.append('};')
        (out/f'{char}_native.c').write_text('\n'.join(lines)+'\n')
        report[char]={'actions':count,'supported':supported,'variants':len(variants),'skipped':skipped}
    (out/'native-extraction-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
