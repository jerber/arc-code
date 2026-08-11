#!/usr/bin/env python3
from collections import deque
N=13
H=set(); FLOOR=set(); PLATE={}; DOOR={}
rowspec=[
 "HHHHHHHHHHHHH",
 "H.....H.....H",
 "H..O..H..G..H",
 "H.....H.....H",
 "H.....H.....H",
 "H.....H.....H",
 "HHgggHHHhhhHH",   # g = green door, h = orange door
 "H.....H.....H",
 "H.....H.....H",
 "H..G..D.....H",   # D = the dot's start cell (floor)
 "H.....H.....H",
 "H.....H.....H",
 "HHHHHHHHHHHHH",
]
for y,r in enumerate(rowspec):
    for x,ch in enumerate(r):
        p=(x,y)
        if ch=='H': H.add(p)
        elif ch=='O': FLOOR.add(p); PLATE[p]='c'
        elif ch=='G': FLOOR.add(p); PLATE[p]='e'
        elif ch=='g': FLOOR.add(p); DOOR[p]='e'
        elif ch=='h': FLOOR.add(p); DOOR[p]='c'
        else: FLOOR.add(p)

# ACTION3 -> L -x, R +x ; ACTION4 -> L +x, R -x ; ACTION1 up, ACTION2 down
MOVES=[('ACTION1',0,-1),('ACTION2',0,1),('ACTION3',-1,0),('ACTION4',1,0)]

def search(L0,R0,D0,dot_presses=False,dot_on_hazard=False):
    def oc(L,R,D):
        s=set()
        for p in (L,R):
            if p in PLATE: s.add(PLATE[p])
        if dot_presses and D in PLATE: s.add(PLATE[D])
        return s
    def ok_avatar(t,colours):
        if t in H: return 'DIE'
        if t not in FLOOR: return False
        if t in DOOR and DOOR[t] not in colours: return False
        return True
    start=(L0,R0,D0,0)
    seen={start:None}; q=deque([start])
    while q:
        st=q.popleft(); L,R,D,mode=st
        if L==R:
            path=[];s=st
            while seen[s]: s,a=seen[s]; path.append(a)
            return path[::-1]
        nxt=[]
        colours=oc(L,R,D)
        if mode==0:
            for name,dx,dy in MOVES:
                dead=False; new=[]
                for p,s_ in ((L,1),(R,-1)):
                    t=(p[0]+dx*s_,p[1]+dy)
                    r=ok_avatar(t,colours)
                    if r=='DIE': dead=True; break
                    new.append(t if (r and t!=D) else p)
                if dead: continue
                nxt.append(((new[0],new[1],D,0),name))
            nxt.append(((L,R,D,1),'SELDOT'))
        else:
            for name,dx,dy in MOVES:
                t=(D[0]+dx,D[1]+dy)
                good = t in FLOOR and t!=L and t!=R and not (t in DOOR and DOOR[t] not in colours)
                if t in H and dot_on_hazard: good=True
                nxt.append(((L,R,t if good else D,1),name))
            nxt.append(((L,R,D,0),'DESELECT'))
        for ns,a in nxt:
            if ns not in seen: seen[ns]=(st,a); q.append(ns)
    return None

if __name__=="__main__":
    for dp in (False,True):
        p=search((2,4),(10,4),(6,9),dot_presses=dp)
        print('dot_presses',dp,'len',len(p) if p else None)
        if p: print(p)
