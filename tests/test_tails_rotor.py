"""Verify local original rotor geometry preserves the flight motion hierarchy."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from extract_native_actions import PE,extract,flying_tail_geometry
pe=PE(Path(r'C:\Program Files (x86)\Steam\steamapps\common\Sonic Adventure DX\system\CHRMODELS_orig.dll'))
checks=[]
for action in range(37,42):
    original,root=extract(pe,'MILES',action);rotor=flying_tail_geometry(pe,original)
    assert len(rotor)==len(original)==68
    assert [(n['parent'],n['animIndex']) for n in rotor]==[(n['parent'],n['animIndex']) for n in original]
    assert rotor[:59]==original[:59] and rotor[67:]==original[67:],'Flight body changed'
    for start in (59,63):
        assert any(rotor[n]['triangles']!=original[n]['triangles'] for n in range(start,start+4))
    assert all(not rotor[n]['flags']&2 for n in (59,63)),'Procedural rotor rotation masked'
    checks.append({'action':action,'bone_layout_preserved':True,'original_rotor_meshes':True})
(ROOT/'docs/tails-rotor-0.1.22.json').write_text(json.dumps({'version':'0.1.22','status':'passed','checks':checks,'actual_zelda_visual_verified':False},indent=2)+'\n')
print('PASS: five flight motions retain their 68-node body layout and use both original rotor meshes.')
