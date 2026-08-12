#!/usr/bin/env python3
"""Two avatars: vertical moves same, horizontal moves MIRRORED."""
from collections import deque
import grid, parse

# action -> (dyL,dxL) ; right gets dx negated
ACTS={'ACTION1':(0,-1),'ACTION2':(0,1),'ACTION4':(1,0),'ACTION3':(-1,0)}

def build(c):
    ny=len(c); nx=len(c[0])
    open_=set(); players=[]
    for y in range(ny):
        for x in range(nx):
            if c[y][x] not in 'bc': open_.add((x,y))
            if c[y][x]=='a': players.append((x,y))
    players.sort()
    return open_,players,nx,ny

def mv(p,dx,dy,open_):
    n=(p[0]+dx,p[1]+dy)
    return n if n in open_ else p

def bfs(open_,pL,pR,goal=None):
    start=(pL,pR); seen={start:None}; q=deque([start])
    while q:
        L,R=q.popleft()
        if (L==R) if goal is None else (L==goal and R==goal):
            path=[];st=(L,R)
            while seen[st]: st,a=seen[st]; path.append(a)
            return path[::-1]
        for a,(dx,dy) in ACTS.items():
            n=(mv(L,dx,dy,open_), mv(R,-dx,dy,open_))
            if n not in seen:
                seen[n]=((L,R),a); q.append(n)
    return None

if __name__=="__main__":
    e=parse.load()
    c=grid.coarse(e[-1][1])
    open_,ps,nx,ny=build(c)
    print('players',ps)
    p=bfs(open_,ps[0],ps[1])
    print(len(p) if p else None, p)
