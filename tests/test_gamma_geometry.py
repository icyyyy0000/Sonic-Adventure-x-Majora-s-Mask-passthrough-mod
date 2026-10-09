"""Check quad coverage through the production importer and Gamma's local assets."""
import json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from extract_models import PE,extract,model_triangles
class Fixture:
    def __init__(self):
        self.data=bytearray(512)
        struct.pack_into('<IIiIIHH',self.data,16,64,0,4,128,160,1,1)
        for i,p in enumerate([(0,0,0),(1,0,0),(0,1,0),(1,1,0)]):struct.pack_into('<fff',self.data,64+i*12,*p)
        struct.pack_into('<HHIIIIII',self.data,128,0x4000,1,192,0,0,0,0,0)
        struct.pack_into('<I',self.data,160,0xffffffff)
        struct.pack_into('<HHHH',self.data,192,0,1,2,3)
    def read(self,addr,fmt):return struct.unpack_from('<'+fmt,self.data,addr)
tris=model_triangles(Fixture(),16)
def signed_area(t):
    a,b,c=t[0];return ((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
assert len(tris)==2 and all(signed_area(t)==.5 for t in tris)
assert tris[1][0]==((0.,1.,0.),(1.,0.,0.),(1.,1.,0.))
sadx=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Sonic Adventure DX')
pe=PE(sadx/'system/CHRMODELS_orig.dll');nodes,_=extract(pe,'E102',0)
quads=0
for node in nodes:
    model=pe.read(node['source'],'II')[1]
    if not model or node['flags']&8:continue
    _,_,_,sets,_,count,_=pe.read(model,'IIiIIHH')
    for i in range(count):
        kind,n=pe.read(sets+i*28,'HH')
        if kind&0xc000==0x4000:quads+=n
triangles=sum(len(n['triangles']) for n in nodes)
generated=(ROOT/'src/generated/gamma_model.c').read_text()
assert quads==343 and triangles==970
assert generated.count('gsSP1Triangle(')==triangles
report={'version':'0.1.21','status':'passed','source_quad_faces':quads,'generated_triangles':triangles,
        'checks':['strip-ordered quad covers unit square with equal winding and no missing half','Gamma generated display list retains all extracted triangles'],
        'actual_zelda_visual_verified':False}
(ROOT/'docs/gamma-geometry-0.1.21.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS Gamma quad coverage and generated geometry')
