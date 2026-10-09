"""Confirm this camera build carries the exact 0.1.18 terrain/character engine."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=ROOT/'release/0.1.18/observer/sadx/TerminaAdventureBridge/TerminaAdventureSADX.dll'
assert digest(ROOT/'build/native/TerminaAdventureSADX.dll')==digest(old)
with zipfile.ZipFile(ROOT/'build/termina_adventure_bridge-0.1.21.nrm') as current, zipfile.ZipFile(ROOT/'release/0.1.18/observer/recomp/termina_adventure_bridge-0.1.18.nrm') as baseline:
    for name in ['mod_binary.bin','mod_syms.bin']:assert current.read(name)==baseline.read(name),name
protocol=(ROOT/'protocol/world_protocol.h').read_text()
assert '#define TA_WORLD_CAPACITY 2048u' in protocol and 'World_v4' in protocol and '81960' in protocol
big=(ROOT/'src/characters/big.c').read_text()
assert 'ta_mesh_line' not in big and 'anchorMisses' not in big and 'BgCheck_EntityLineTest2(&play->colCtx,&a,&b' in big
assert not (ROOT/'src/host/mesh.c').exists()
result={'version':'0.1.21','status':'passed','collision_baseline':'0.1.18','companion_sha256':digest(old),
    'checks':['shipped companion bytes exactly match 0.1.18','terrain observer code and symbol metadata exactly match 0.1.18','world mapping v4, 2048 triangles, 81960-byte packet restored','Big entity casts and anchor rechecks restored; 0.1.19 mesh-query module removed']}
(ROOT/'docs/collision-rollback-0.1.21.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS collision rollback: exact 0.1.18 companion and terrain observer, original world ABI and Big surface queries.')
