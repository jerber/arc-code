#!/usr/bin/env python3
"""Plan the next leg for an L8 rectangle: BFS to goal, cut the plan at the first squeeze."""
import sim, rect3, parse, sys
def setup():
    bl=parse.load()
    g=bl[[i for i,(h,_) in enumerate(bl) if h.startswith("action 450")][0]][1][-1][1]
    sw=sim.swatch_blocks(g)+[('a',{(0,29),(0,30),(0,31)})]
    def dil(b):
        o=set()
        for x,y in b:
            for dx in(-1,0,1):
                for dy in(-1,0,1): o.add((x+dx,y+dy))
        return o
    return rect3.Game(sim.obstacles(g),[(c,dil(b)) for c,b in sw],26)
def plan(start,goal,G=None,banned=()):
    G=G or setup()
    st,p=G.bfs(start,goal,banned=banned)
    if p is None: return None,None,None
    D=dict(rect3.MOVES); s=start; cut=len(p); trace=[]
    for i,a in enumerate(p):
        ns=G.step(s,D[a]); r=G.recolour(ns)
        sq = ns[2]!=s[2]
        trace.append((i+1,a,r,sq))
        s=r
        if sq: cut=i+1; break
    return p,cut,trace
if __name__=="__main__":
    G=setup()
    for vg in (0,1):
        for hg in (0,1):
            start=(48,6,22,'9',vg,hg)
            p,cut,tr=plan(start,lambda x: x[:4]==(6,45,16,'6'),G)
            if p is None: print(vg,hg,"NO PLAN"); continue
            print(f"vg={vg} hg={hg} total={len(p)} first squeeze at {cut}: state {tr[-1][2] if tr else None}")
            print("   prefix:"," ".join(p[:cut]))
