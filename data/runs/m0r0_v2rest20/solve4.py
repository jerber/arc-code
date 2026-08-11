#!/usr/bin/env python3
"""Full BFS over (avatarL, avatarR, dot, mode) for the mirror-pair game."""
from collections import deque
import solve3

MOVES=[('ACTION1',0,-1),('ACTION2',0,1),('ACTION3',-1,0),('ACTION4',1,0)]

def search(floor, hazard, L0, R0, D0, dot_into_hazard=False, mode0=0, extra_dots=()):
    """floor: set of open cells (excluding hazards & walls). hazard: set.
    Returns list of action strings ('ACTION1'.. or ('CLICK',cell))."""
    start=(L0,R0,D0,mode0)
    seen={start:None}; q=deque([start])
    while q:
        st=q.popleft()
        L,R,D,mode=st
        if L==R:
            path=[]; s=st
            while seen[s]: s,a=seen[s]; path.append(a)
            return path[::-1]
        succ=[]
        if mode==0:
            for name,dx,dy in MOVES:
                ok=True; new=[]
                for p,s_ in ((L,1),(R,-1)):
                    t=(p[0]+dx*s_,p[1]+dy)
                    if t in hazard: ok=False; break
                    if t in floor and t!=D: new.append(t)
                    else: new.append(p)
                if ok: succ.append(((new[0],new[1],D,0),name))
            succ.append(((L,R,D,1),('CLICK','dot')))
        else:
            for name,dx,dy in MOVES:
                t=(D[0]+dx,D[1]+dy)
                if t in hazard:
                    if not dot_into_hazard: continue
                    nd=t
                elif t in floor and t!=L and t!=R: nd=t
                else: nd=D
                succ.append(((L,R,nd,1),name))
            succ.append(((L,R,D,0),('CLICK','off')))
        for ns,a in succ:
            if ns not in seen:
                seen[ns]=(st,a); q.append(ns)
    return None
