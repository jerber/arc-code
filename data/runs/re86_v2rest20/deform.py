#!/usr/bin/env python3
"""BFS over multi-part shape states with obstacle blocking (parts desync)."""
import collections, itertools

W,H=64,63
MOVES=[('ACTION1',(0,-3)),('ACTION2',(0,3)),('ACTION3',(-3,0)),('ACTION4',(3,0))]

def cells_of(kind,c,r):
    x,y=c; s=set()
    if kind=='hline':
        for k in range(-r,r+1): s.add((x+k,y))
    elif kind=='vline':
        for k in range(-r,r+1): s.add((x,y+k))
    elif kind=='dline':
        for k in range(-r,r+1): s.add((x+k,y+k))
    elif kind=='aline':
        for k in range(-r,r+1): s.add((x+k,y-k))
    elif kind=='plus':
        for k in range(-r,r+1): s.add((x+k,y)); s.add((x,y+k))
    elif kind=='X':
        for k in range(-r,r+1): s.add((x+k,y+k)); s.add((x+k,y-k))
    elif kind=='diamond':
        for dx in range(-r,r+1):
            d=r-abs(dx); s.add((x+dx,y+d)); s.add((x+dx,y-d))
    elif kind=='square':
        for k in range(-r,r+1):
            s.add((x+k,y-r)); s.add((x+k,y+r)); s.add((x-r,y+k)); s.add((x+r,y+k))
    else: raise ValueError(kind)
    return s

def onboard(s): return {p for p in s if 0<=p[0]<W and 0<=p[1]<H}

def step(parts, state, d, obst):
    """parts: [(kind,r)]; state: tuple of centres; returns new state"""
    new=[]
    for (kind,r),c in zip(parts,state):
        nc=(c[0]+d[0],c[1]+d[1])
        if onboard(cells_of(kind,nc,r)) & obst: new.append(c)
        else: new.append(nc)
    return tuple(new)

def covered(parts,state,boxes):
    u=set()
    for (kind,r),c in zip(parts,state): u|=cells_of(kind,c,r)
    return all(b in u for b in boxes)

def search(parts, start, obst, boxes, lo=-6, hi=69, maxstates=4000000, avoid=None):
    """BFS to any state covering all boxes. avoid(state)->bool forbids states."""
    seen={start:None}
    q=collections.deque([start])
    while q:
        s=q.popleft()
        if covered(parts,s,boxes):
            path=[]
            cur=s
            while seen[cur]:
                cur,name=seen[cur]; path.append(name)
            return s, path[::-1]
        for name,d in MOVES:
            ns=step(parts,s,d,obst)
            if ns in seen or ns==s: continue
            if any(not(lo<=c[0]<=hi and lo<=c[1]<=hi) for c in ns): continue
            if avoid and avoid(ns): continue
            seen[ns]=(s,name); q.append(ns)
        if len(seen)>maxstates: break
    return None,None
