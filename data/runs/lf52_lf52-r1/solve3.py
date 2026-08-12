import sys
sys.setrecursionlimit(100000)

BIG=[(1,1),(2,1),(4,1),(5,1),(1,2),(2,2),(4,2),(5,2),
     (1,3),(2,3),(3,3),(4,3),(1,4),(2,4),(3,4),(4,4)]
P4=[(1,8),(2,8),(3,8),(4,8),(1,9),(2,9),(3,9)]
R=[(10,2)]+[(x,y) for y in range(1,10) for x in (11,12)]+[(13,3),(14,3),(13,5),(14,5),(13,7)]
panels={'BIG':BIG,'P4':P4,'R':R}
cells=[]
for name,cs in panels.items(): cells+=cs
cells=sorted(set(cells))
cells+=['S1','S2']
idx={c:i for i,c in enumerate(cells)}

triples=[]
def add(a,b,c):
    if a in idx and b in idx and c in idx: triples.append((idx[a],idx[b],idx[c]))
for name,cs in panels.items():
    S=set(cs)
    for (x,y) in cs:
        for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
            b=(x+dx,y+dy); c=(x+2*dx,y+2*dy)
            if b in S and c in S: add((x,y),b,c)
# shuttle docks
add('S1',(5,2),(4,2)); add((4,2),(5,2),'S1')
add('S1',(10,2),(11,2)); add((11,2),(10,2),'S1')
add('S2',(4,8),(3,8)); add((3,8),(4,8),'S2')
add('S2',(11,8),(12,8)); add((12,8),(11,8),'S2')
triples=sorted(set(triples))

START=[(2,2),(5,2),(2,3),(4,3),(3,4),(2,8),(4,8),(10,2),(12,3),(13,3),(12,5),(13,5),(11,7),(12,8)]
start=0
for c in START: start|=1<<idx[c]

def popcount(n): return bin(n).count('1')
fail=set()
def dfs(state,path):
    if popcount(state)==1: return path
    if state in fail: return None
    for a,b,c in triples:
        if (state>>a&1) and (state>>b&1) and not (state>>c&1):
            ns=state & ~(1<<a) & ~(1<<b) | (1<<c)
            r=dfs(ns,path+[(cells[a],cells[c])])
            if r is not None: return r
    fail.add(state)
    return None
import time
t=time.time()
r=dfs(start,[])
print('elapsed',round(time.time()-t,1),'fail states',len(fail))
if r:
    print('SOLUTION',len(r),'jumps')
    for m in r: print('  ',m)
else: print('NO SOLUTION')
