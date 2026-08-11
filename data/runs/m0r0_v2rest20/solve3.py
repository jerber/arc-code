#!/usr/bin/env python3
"""Generic mirror-pair solver on a coarse block grid."""
from collections import deque, Counter
import parse

ACTS={'ACTION1':(0,-1),'ACTION2':(0,1),'ACTION3':(-1,0),'ACTION4':(1,0)}

def coarse(g,ox,oy,w,nx,ny):
    out=[]
    for by in range(ny):
        row=[]
        for bx in range(nx):
            c=Counter(g[oy+by*w+dy][ox+bx*w+dx] for dy in range(w) for dx in range(w))
            row.append(''.join(sorted(c)))
        out.append(row)
    return out

def analyse(c, floor, avatar='a'):
    ny=len(c); nx=len(c[0])
    open_=set(); ps=[]
    for y in range(ny):
        for x in range(nx):
            v=c[y][x]
            if v in floor or v==avatar: open_.add((x,y))
            if v==avatar: ps.append((x,y))
    ps.sort()
    return open_,ps

def mv(p,dx,dy,open_):
    n=(p[0]+dx,p[1]+dy)
    return n if n in open_ else p

def bfs(open_,pL,pR,maxstates=4000000):
    start=(pL,pR); seen={start:None}; q=deque([start])
    while q:
        L,R=q.popleft()
        if L==R:
            path=[];st=(L,R)
            while seen[st]: st,a=seen[st]; path.append(a)
            return path[::-1]
        for a,(dx,dy) in ACTS.items():
            n=(mv(L,dx,dy,open_), mv(R,-dx,dy,open_))
            if n not in seen:
                seen[n]=((L,R),a); q.append(n)
    return None

def simulate(open_,pL,pR,path):
    for a in path:
        dx,dy=ACTS[a]
        pL=mv(pL,dx,dy,open_); pR=mv(pR,-dx,dy,open_)
    return pL,pR
