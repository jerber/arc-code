import sys
from functools import lru_cache
cells=[]
for j in range(3):
    for i in range(7): cells.append(('A',i,j))
cells.append(('O',0,0))
for j in range(2):
    for i in range(2): cells.append(('B',i,j))
idx={c:k for k,c in enumerate(cells)}

triples=[]
def add(a,b,c):
    if a in idx and b in idx and c in idx: triples.append((idx[a],idx[b],idx[c]))
for j in range(3):
    for i in range(7):
        add(('A',i,j),('A',i+1,j),('A',i+2,j)); add(('A',i,j),('A',i-1,j),('A',i-2,j))
        add(('A',i,j),('A',i,j+1),('A',i,j+2)); add(('A',i,j),('A',i,j-1),('A',i,j-2))
for j in range(2):
    for i in range(2):
        add(('B',i,j),('B',i+1,j),('B',i+2,j)); add(('B',i,j),('B',i-1,j),('B',i-2,j))
        add(('B',i,j),('B',i,j+1),('B',i,j+2)); add(('B',i,j),('B',i,j-1),('B',i,j-2))
# pipe chain: A(5,1)-A(6,1)-O-B(0,1)-B(1,1)
chain=[('A',4,1),('A',5,1),('A',6,1),('O',0,0),('B',0,1),('B',1,1)]
for k in range(len(chain)-2):
    add(chain[k],chain[k+1],chain[k+2]); add(chain[k+2],chain[k+1],chain[k])
triples=list(set(triples))

start=0
for c in [('A',1,1),('A',2,1),('A',4,1),('A',6,1),('O',0,0),('B',0,1)]:
    start|=1<<idx[c]

seen=set()
def dfs(state,path):
    if bin(state).count('1')==1: return path
    if state in seen: return None
    seen.add(state)
    for a,b,c in triples:
        if state>>a&1 and state>>b&1 and not (state>>c&1):
            ns=state & ~(1<<a) & ~(1<<b) | (1<<c)
            r=dfs(ns,path+[(cells[a],cells[c])])
            if r: return r
    return None
r=dfs(start,[])
print('solution' if r else 'NONE')
if r:
    for m in r: print(m)
