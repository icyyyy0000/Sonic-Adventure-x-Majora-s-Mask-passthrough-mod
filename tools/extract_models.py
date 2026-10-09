"""Read the user's SADX PE data without executing it. No external packages required.

Exports untextured Ninja BASIC geometry as N64 display lists. Generated files contain
local game assets and must not be redistributed. The original DLL is never changed.
"""
import argparse
import json
import struct
from pathlib import Path


class PE:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        pe = self.u32(0x3c)
        if self.data[pe:pe + 4] != b'PE\0\0':
            raise ValueError('Not a PE file')
        opt = pe + 24
        if self.u16(opt) != 0x10b:
            raise ValueError('Expected 32-bit SADX DLL')
        self.base = self.u32(opt + 28)
        self.sections = []
        for i in range(self.u16(pe + 6)):
            off = opt + self.u16(pe + 20) + i * 40
            size, rva, rawsize, raw = struct.unpack_from('<IIII', self.data, off + 8)
            self.sections.append((rva, max(size, rawsize), raw, rawsize))
        exp = self.rva(self.u32(opt + 96))
        count = self.u32(exp + 24)
        funcs, names, ords = [self.rva(self.u32(exp + off)) for off in (28, 32, 36)]
        self.exports = {}
        for i in range(count):
            nameoff = self.rva(self.u32(names + i * 4))
            name = self.data[nameoff:self.data.index(0, nameoff)].decode('ascii')
            ordinal = self.u16(ords + i * 2)
            self.exports[name] = self.base + self.u32(funcs + ordinal * 4)

    def u16(self, off):
        return struct.unpack_from('<H', self.data, off)[0]

    def u32(self, off):
        return struct.unpack_from('<I', self.data, off)[0]

    def rva(self, addr):
        for rva, size, raw, rawsize in self.sections:
            if rva <= addr < rva + size:
                delta = addr - rva
                if delta >= rawsize:
                    raise ValueError('Pointer into uninitialized PE section')
                return raw + delta
        raise ValueError(f'Invalid RVA {addr:x}')

    def read(self, addr, fmt):
        return struct.unpack_from('<' + fmt, self.data, self.rva(addr - self.base))

    def pointer(self, addr):
        return self.read(addr, 'I')[0]


ROSTER = [('sonic', 'SONIC', [1, 6, 10, 14]), ('tails', 'MILES', [79, 80, 13, 17]),
          ('knuckles', 'KNUCKLES', [82, 57, 6, 15]), ('amy', 'AMY', [69, 45, 6, 1]),
          ('big', 'BIG', [23, 24, 13, 0]), ('gamma', 'E102', [0, 3, 16, 49])]


def textures(path):
    """Decode the rectangular 16-bit PVR textures in the user's converted PC data."""
    data = path.read_bytes()
    result = []
    cursor = 0
    while True:
        off = data.find(b'PVRT', cursor)
        if off < 0:
            break
        size = struct.unpack_from('<I', data, off + 4)[0]
        pix, layout, reserved, w, h = struct.unpack_from('<BBHHH', data, off + 8)
        if layout != 9 or pix not in (0, 1, 2):
            raise ValueError(f'Unsupported texture format {pix}/{layout} in {path}')
        values = struct.unpack_from('<' + 'H' * (w * h), data, off + 16)
        rgba = []
        for v in values:
            if pix == 0:
                r, g, b, a = (v >> 10) & 31, (v >> 5) & 31, v & 31, (v >> 15) & 1
                rgba.append((r * 255 // 31, g * 255 // 31, b * 255 // 31, a * 255))
            elif pix == 1:
                rgba.append((((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31, 255))
            else:
                rgba.append((((v >> 8) & 15) * 17, ((v >> 4) & 15) * 17, (v & 15) * 17, ((v >> 12) & 15) * 17))
        nw, nh = min(32, w), min(32, h)
        resized = [rgba[min(h - 1, y * h // nh) * w + min(w - 1, x * w // nw)] for y in range(nh) for x in range(nw)]
        result.append((nw, nh, resized))
        cursor = off + 8 + size
    return result


def model_triangles(pe, addr):
    points, normals, npoint, sets, mats, nsets, nmats = pe.read(addr, 'IIiIIHH')
    if not 0 < npoint <= 65535 or not 0 <= nsets <= 1024:
        raise ValueError('Invalid model counts')
    xyz = [pe.read(points + i * 12, 'fff') for i in range(npoint)]
    result = []
    for s in range(nsets):
        kindmat, count, mesh, attrs, norm, colors, uv, buf = pe.read(sets + s * 28, 'HHIIIIII')
        mat = kindmat & 0x3fff
        diffuse = pe.read(mats + mat * 20, 'I')[0] if mat < nmats else 0xffffffff
        texid = pe.read(mats + mat * 20 + 12, 'I')[0] & 65535 if mat < nmats else 0
        color = ((diffuse >> 16) & 255, (diffuse >> 8) & 255, diffuse & 255, 255)
        kind = kindmat & 0xc000
        cursor = mesh
        uvCursor = 0
        for _ in range(count):
            if kind in (0, 0x4000):
                length = 3 if kind == 0 else 4
                indices = pe.read(cursor, 'H' * length)
                cursor += 2 * length
                triangles = [(0, 1, 2)] if length == 3 else [(0, 1, 2), (2, 1, 3)]
            else:
                raw = pe.read(cursor, 'H')[0]
                length = raw & 0x7fff
                if not 3 <= length <= 65535:
                    raise ValueError('Invalid strip size')
                indices = pe.read(cursor + 2, 'H' * length)
                cursor += 2 + 2 * length
                if kind == 0xc000:
                    triangles = [(i, i + 1 + ((i ^ (raw >> 15)) & 1),
                                  i + 2 - ((i ^ (raw >> 15)) & 1)) for i in range(length - 2)]
                else:
                    triangles = [(0, i, i + 1) for i in range(1, length - 1)]
            for tri in triangles:
                ids = [indices[i] for i in tri]
                if any(i >= npoint for i in ids):
                    raise ValueError('Vertex index outside model')
                if len(set(ids)) == 3:
                    texcoords = tuple(pe.read(uv + (uvCursor + i) * 4, 'hh') for i in tri) if uv else ((0, 0),) * 3
                    result.append((tuple(xyz[i] for i in ids), color, texcoords, texid))
            uvCursor += length
    return result


def extract(pe, prefix, actionIndex):
    action = pe.pointer(pe.exports[f'___{prefix}_ACTIONS'] + actionIndex * 4)
    root, motion = pe.read(action, 'II')
    nodes = []
    visited = set()

    animIndex = 0
    def walk(addr, parent):
        nonlocal animIndex
        while addr:
            if addr in visited:
                raise ValueError('Cycle in Ninja object tree')
            visited.add(addr)
            flags, model, *rest = pe.read(addr, 'IIfffiiifffII')
            pos, ang, scale = rest[:3], rest[3:6], rest[6:9]
            child, sibling = rest[9:]
            idx = len(nodes)
            bone = -1 if flags & 64 else animIndex
            if bone >= 0:
                animIndex += 1
            nodes.append(dict(source=addr,parent=parent, flags=flags, pos=pos, ang=ang, scale=scale, animIndex=bone,
                              triangles=model_triangles(pe, model) if model and not flags & 8 else []))
            if child and not flags & 16:
                walk(child, idx)
            addr = sibling
    walk(root, -1)
    return nodes, root


def extract_animation(pe, prefix, actionIndex, root, count, include_scale=False):
    action = pe.pointer(pe.exports[f'___{prefix}_ACTIONS'] + actionIndex * 4)
    obj, motion = pe.read(action, 'II')
    mdata, frames, kind, inp = pe.read(motion, 'IIHH')
    factors = [bit for bit in (1, 2, 4) if kind & bit]
    if kind & ~7 or inp & 15 != len(factors):
        return None
    if obj != root:
        alternate, _ = extract(pe, prefix, actionIndex)
        canonical = []
        # Compare tree topology before applying another object's motion.
        def topology(addr, parent=-1):
            while addr:
                flags, model, *rest = pe.read(addr, 'IIfffiiifffII')
                idx = len(canonical)
                canonical.append(parent)
                if rest[9] and not flags & 16: topology(rest[9], idx)
                addr = rest[10]
        topology(root)
        if [n['parent'] for n in alternate] != canonical:
            return None
    bones = []
    for i in range(count):
        row = pe.read(mdata + i * len(factors) * 8, 'I' * (len(factors) * 2))
        pointers, counts = dict(zip(factors, row[:len(factors)])), dict(zip(factors, row[len(factors):]))
        pos, rot, np, nr = pointers.get(1, 0), pointers.get(2, 0), counts.get(1, 0), counts.get(2, 0)
        if np > frames + 1 or nr > frames + 1:
            raise ValueError('Invalid motion key count')
        scale, ns = pointers.get(4, 0), counts.get(4, 0)
        if ns > frames + 1: raise ValueError('Invalid scale key count')
        channels=([pe.read(pos + k * 16, 'Ifff') for k in range(np)] if pos else [],
                  [pe.read(rot + k * 16, 'Iiii') for k in range(nr)] if rot else [])
        if include_scale: channels+=([pe.read(scale+k*16,'Ifff') for k in range(ns)] if scale else [],)
        bones.append(channels)
    return frames, bones


def cfloat(v):
    return f'{v:.6f}f'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sadx', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=Path('src/generated'))
    args = parser.parse_args()
    dll = args.sadx / 'system' / 'CHRMODELS_orig.dll'
    pe = PE(dll)
    args.output.mkdir(parents=True, exist_ok=True)
    report = {}
    for char, prefix, actions in ROSTER:
        nodes, root = extract(pe, prefix, actions[0])
        texs = textures(args.sadx / 'system' / f'{prefix}.PVM')
        lines = ['/* LOCAL GAME ASSETS: regenerate from your own SADX; do not distribute. */',
                 '#include "render/character_model.h"']
        for ti, (w, h, rgba) in enumerate(texs):
            lines.append(f'static u16 {char}_tex{ti}[] __attribute__((aligned(8))) = {{')
            for row in range(h):
                values = [(r >> 3) << 11 | (g >> 3) << 6 | (b >> 3) << 1 | int(a >= 128) for r, g, b, a in rgba[row*w:(row+1)*w]]
                lines.append('    ' + ','.join(f'0x{v:04x}' for v in values) + ',')
            lines.append('};')
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
                    lines.append(f'    gsDPLoadTextureBlock({char}_tex{ti}, G_IM_FMT_RGBA, G_IM_SIZ_16b, {w}, {h}, 0, G_TX_WRAP, G_TX_WRAP, {w.bit_length()-1}, {h.bit_length()-1}, G_TX_NOLOD, G_TX_NOLOD),')
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
        clips = []
        boneCount = sum(n['animIndex'] >= 0 for n in nodes)
        for ci, actionIndex in enumerate(actions):
            clip = extract_animation(pe, prefix, actionIndex, root, boneCount)
            clips.append(clip)
            if clip is None:
                continue
            frames, bones = clip
            for bi, (posKeys, rotKeys) in enumerate(bones):
                if posKeys:
                    lines.append(f'static TA_PosKey {char}_p{ci}_{bi}[] = {{')
                    lines += ['    {%d,{%s}},' % (key[0], ','.join(cfloat(v) for v in key[1:])) for key in posKeys]
                    lines.append('};')
                if rotKeys:
                    lines.append(f'static TA_RotKey {char}_r{ci}_{bi}[] = {{')
                    lines += ['    {%d,{%s}},' % (key[0], ','.join(str((v+32768)%65536-32768) for v in key[1:])) for key in rotKeys]
                    lines.append('};')
            lines.append(f'static TA_BoneTrack {char}_tracks{ci}[] = {{')
            for bi, (posKeys, rotKeys) in enumerate(bones):
                pp = f'{char}_p{ci}_{bi}' if posKeys else 'NULL'
                rp = f'{char}_r{ci}_{bi}' if rotKeys else 'NULL'
                lines.append(f'    {{{len(posKeys)},{len(rotKeys)},{pp},{rp},0,NULL}},')
            lines.append('};')
        lines.append(f'static TA_Animation {char}_clips[] = {{')
        for ci, clip in enumerate(clips):
            lines.append(f'    {{{clip[0]},{char}_tracks{ci}}},' if clip else '    {0,NULL},')
        lines += ['};', f'TA_CharacterModel ta_model_{char} = {{{len(nodes)}, {char}_nodes, {char}_clips}};']
        (args.output / f'{char}_model.c').write_text('\n'.join(lines) + '\n')
        report[char] = dict(nodes=len(nodes), triangles=sum(len(n['triangles']) for n in nodes), textures=len(texs),
                            animation_actions=actions, animation_supported=[c is not None for c in clips])
    (args.output / 'extraction-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
