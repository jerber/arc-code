#!/usr/bin/env python3
from collections import deque
import l6
FLOOR,H,PLATE,DOOR,MOVES=l6.FLOOR,l6.H,l6.PLATE,l6.DOOR,l6.MOVES

def search(L0,R0,D0,frozen_press=True,dot_through_doors=True,dot_presses=False):
    def oc(L,R,D,mode):
        s=set()
        if mode==0 or frozen_press:
            for p in (L,R):
                if p in PLATE: s.add(PLATE[p])
        if dot_presses and D in PLATE: s.add(PLATE[D])
        return s
    start=(L0,R0,D0,0); seen={start:None}; q=deque([start])
    while q:
        st=q.popleft(); L,R,D,mode=st
        if L==R:
            path=[];s=st
            while seen[s]: s,a=seen[s]; path.append(a)
            return path[::-1]
        cols=oc(L,R,D,mode); nxt=[]
        if mode==0:
            for name,dx,dy in MOVES:
                dead=False; new=[]
                for p,s_ in ((L,1),(R,-1)):
                    t=(p[0]+dx*s_,p[1]+dy)
                    if t in H: dead=True; break
                    good = t in FLOOR and t!=D and not (t in DOOR and DOOR[t] not in cols)
                    new.append(t if good else p)
                if dead: continue
                nxt.append(((new[0],new[1],D,0),name))
            nxt.append(((L,R,D,1),'SELDOT'))
        else:
            for name,dx,dy in MOVES:
                t=(D[0]+dx,D[1]+dy)
                good = t in FLOOR and t!=L and t!=R
                if t in DOOR and not (dot_through_doors and DOOR[t] in cols): good=False
                nxt.append(((L,R,t if good else D,1),name))
            nxt.append(((L,R,D,0),'DESELECT'))
        for ns,a in nxt:
            if ns not in seen: seen[ns]=(st,a); q.append(ns)
    return None

if __name__=="__main__":
    import itertools
    for fp,dtd,dp in itertools.product([True,False],[True,False],[False,True]):
        p=search((2,4),(10,4),(6,9),fp,dtd,dp)
        print('frozen_press=%-5s dot_thru_doors=%-5s dot_presses=%-5s -> %s'%(fp,dtd,dp,len(p) if p else None))
