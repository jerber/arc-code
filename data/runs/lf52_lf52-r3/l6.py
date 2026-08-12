import game,heapq
CELLS={}
for y in (12,18,24,30):
    for x in (12,18,24,30): CELLS[(x,y)]='.'
for y in (36,42,48):
    for x in (12,18,24,30,36,42): CELLS[(x,y)]='.'
CELLS[(24,54)]='.'
for x in (90,96,102,108): CELLS[(x,12)]='.'
for x in (90,96,102,108,114,120,126,132): CELLS[(x,18)]='.'
for x in (96,102): CELLS[(x,24)]='.'
for p in [(126,42),(132,42),(126,48),(126,54)]: CELLS[p]='.'
PIV={(90,24),(108,24)}
REDS={(18,18)}
for p in [(18,24),(12,48),(24,54),(96,18),(126,48)]: CELLS[p]='P'
NODES=set()
for x in range(48,109,6): NODES.add((x,42))
for x in (90,108):
    NODES.add((x,36)); NODES.add((x,30))
from collections import defaultdict
EDGES=defaultdict(set)
def link(a,b): EDGES[a].add(b); EDGES[b].add(a)
for x in range(48,103,6): link((x,42),(x+6,42))
for x in (90,108):
    link((x,42),(x,36)); link((x,36),(x,30))
CARTS={(48,42):('S','.'),(54,42):('S','.')}
E=dict(cells=CELLS,pivots=PIV,reds=REDS,nodes=NODES,edges=EDGES,carts=CARTS,off=(0,0))
