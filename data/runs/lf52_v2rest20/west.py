"""Search the west panel: how many pieces can reach the shuttle dock?"""
import sim
from collections import deque
CELLS={c for c in sim.CELLS if c[0]<=7}
START=frozenset({((3,3),'R'),((3,4),'G'),((2,8),'G'),((4,9),'G')})
def moves(st):
    d=dict(st)
    out=[]
    for a,av in d.items():
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            b=(a[0]+dx,a[1]+dy); c=(a[0]+2*dx,a[1]+2*dy)
            if b not in d: continue
            if c not in CELLS or c in d: continue
            bv=d[b]
            nd=dict(d); del nd[a]
            if av=='G' and bv=='G': del nd[b]
            nd[c]=av
            out.append((frozenset(nd.items()),(a,b,c)))
    return out
seen={START:None}
q=deque([START])
best={}
while q:
    st=q.popleft()
    d=dict(st)
    # score: pieces at (6,7)&(7,7) means export possible
    key=(sum(1 for v in d.values() if v=='G'),tuple(sorted(d.items())))
    for ns,mv in moves(st):
        if ns in seen: continue
        seen[ns]=(st,mv); q.append(ns)
print('states',len(seen))
# find states where a piece is at (6,7) and another at (7,7)
cands=[s for s in seen if dict(s).get((6,7)) and dict(s).get((7,7))]
print('dock-ready states',len(cands))
import collections
cnt=collections.Counter()
for s in cands:
    d=dict(s); cnt[(len(d),sum(1 for v in d.values() if v=='G'),d[(6,7)],d[(7,7)])]+=1
for k,v in sorted(cnt.items()): print(k,v)
