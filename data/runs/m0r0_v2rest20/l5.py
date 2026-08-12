#!/usr/bin/env python3
from collections import deque
W,H=15,13
WALL='W'
# cell map: '.'=floor, 'W'=wall, 'P?'=plate colour, 'D?'=door colour
rows=[
 ".. .  Pf .  .  .  .  .  .  .  .  .  .  .",  # placeholder
]
grid={}
def setrow(y, items):
    for x,v in enumerate(items): grid[(x,y)]=v
setrow(0,['.','.','.','Pf','.','.','.','.','.','.','.','.','.','.','.'])
for y in (1,2,3): setrow(y,['.']*15)
setrow(4,['W','W','W','De','De','De','W','W','W','W','Df','Df','Df','W','W'])
setrow(5,['.','.','.','.','.','.','.','W','Pe','.','.','.','.','.','Pc'])
setrow(6,['.','.','.','.','.','.','.','W','W','.','.','.','.','.','W'])
setrow(7,['.','.','.','.','.','.','.','W','.','.','.','.','.','.','.'])
setrow(8,['W','W','Dc','Dc','Dc','W','W','W','W','W','Df','Df','Df','W','W'])
setrow(9,['.','.','.','.','.','.','.','W','.','.','.','.','.','.','.'])
setrow(10,['.','.','.','W','.','.','.','W','.','.','.','.','.','.','.'])
setrow(11,['.','.','.','Pf','.','.','.','W','.','.','.','.','.','.','.'])
setrow(12,['.','.','.','.','.','.','.','W','.','.','.','.','.','.','.'])

# L5 sign convention: ACTION3 -> L +x, R -x ; ACTION4 -> L -x, R +x
MOVES=[('ACTION1',0,-1),('ACTION2',0,1),('ACTION3',1,0),('ACTION4',-1,0)]

def opencolours(L,R):
    s=set()
    for p in (L,R):
        v=grid.get(p,'W')
        if v.startswith('P'): s.add(v[1])
    return s

def passable(p, oc):
    v=grid.get(p)
    if v is None or v=='W': return False
    if v.startswith('D'): return v[1] in oc
    return True

def step(L,R,dx,dy):
    oc=opencolours(L,R)
    nL=(L[0]+dx,L[1]+dy); nR=(R[0]-dx,R[1]+dy)
    if not passable(nL,oc): nL=L
    if not passable(nR,oc): nR=R
    # safety: nobody may end standing on a door that is now shut
    oc2=opencolours(nL,nR)
    for p in (nL,nR):
        v=grid.get(p,'W')
        if v.startswith('D') and v[1] not in oc2: return None
    return (nL,nR)

def bfs(L0,R0):
    st=(L0,R0); seen={st:None}; q=deque([st])
    while q:
        L,R=q.popleft()
        if L==R:
            path=[];s=(L,R)
            while seen[s]: s,a=seen[s]; path.append(a)
            return path[::-1]
        for name,dx,dy in MOVES:
            r=step(L,R,dx,dy)
            if r is None or r in seen: continue
            seen[r]=((L,R),name); q.append(r)
    return None

if __name__=="__main__":
    p=bfs((2,9),(12,9))
    print('len',len(p) if p else None)
    print(p)
    if p:
        L,R=(2,9),(12,9)
        for a in p:
            dx,dy=dict((n,(x,y)) for n,x,y in MOVES)[a]
            L,R=step(L,R,dx,dy)
            print(a,L,R,sorted(opencolours(L,R)))
