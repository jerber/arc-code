#!/usr/bin/env python3
from collections import deque
import grid, parse

DIRS={'U':(0,-1),'D':(0,1),'L':(-1,0),'R':(1,0)}

def build(c):
    ny=len(c); nx=len(c[0])
    open_=set(); players=[]
    for y in range(ny):
        for x in range(nx):
            v=c[y][x]
            if v!='b' and v!='c':
                open_.add((x,y))
            if v=='a': players.append((x,y))
    return open_,players,nx,ny

def step(pos,d,open_):
    dx,dy=DIRS[d]
    n=(pos[0]+dx,pos[1]+dy)
    return n if n in open_ else pos

def bfs(open_, ps):
    start=tuple(sorted(ps))
    seen={start:None}
    q=deque([start])
    while q:
        st=q.popleft()
        if len(set(st))==1:
            path=[]
            while seen[st]:
                st,d=seen[st]; path.append(d)
            return path[::-1]
        for d in DIRS:
            nx_=tuple(sorted(step(p,d,open_) for p in st))
            if nx_ not in seen:
                seen[nx_]=(st,d)
                q.append(nx_)
    return None

if __name__=="__main__":
    e=parse.load()
    c=grid.coarse(e[-1][1])
    open_,ps,nx,ny=build(c)
    print('players',ps,'open',len(open_))
    p=bfs(open_,ps)
    print('path',p, len(p) if p else None)
