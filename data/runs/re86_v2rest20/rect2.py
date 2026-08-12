#!/usr/bin/env python3
"""Rectangle-ring model v2: translate unless the translated shape overlaps an
obstacle, in which case it SQUEEZES (leading edge stays, trailing edge advances,
perpendicular dimension grows by 3, alternating which end extends).
Moves that would take the shape's centre off the board are refused."""
import collections
MOVES=[('ACTION1',(0,-3)),('ACTION2',(0,3)),('ACTION3',(-3,0)),('ACTION4',(3,0))]
W,H=64,63
def onb(p): return 0<=p[0]<W and 0<=p[1]<H

class Game:
    def __init__(self,obst,sw,budget):
        self.obst=obst; self.sw=sw; self.b=budget
    def cells(self,L,T,w):
        h=self.b-w; R=L+w-1; B=T+h-1; s=set()
        for x in range(L,R+1): s.add((x,T)); s.add((x,B))
        for y in range(T,B+1): s.add((L,y)); s.add((R,y))
        return s
    def hits(self,L,T,w):
        return any(p in self.obst for p in self.cells(L,T,w) if onb(p))
    def centre_ok(self,L,T,w):
        h=self.b-w
        return 0<=2*L+w-1<=2*(W-1) and 0<=2*T+h-1<=2*(H-1)
    def step(self,state,d):
        L,T,w,col,vg,hg=state; h=self.b-w; dx,dy=d
        nL,nT=L+dx,T+dy
        if not self.centre_ok(nL,nT,w): return None
        if not self.hits(nL,nT,w): return (nL,nT,w,col,vg,hg)
        # squeeze
        if dx:
            if w-3<1: return None
            nw=w-3; sL=L+3 if dx>0 else L
            sT=T-3 if vg==0 else T
            ns=(sL,sT,nw,col,1-vg,hg)
        else:
            if h-3<1: return None
            nw=w+3; sT=T+3 if dy>0 else T
            sL=L-3 if hg==0 else L
            ns=(sL,sT,nw,col,vg,1-hg)
        if not self.centre_ok(ns[0],ns[1],ns[2]): return None
        if self.hits(ns[0],ns[1],ns[2]): return None
        return ns
    def recolour(self,s):
        L,T,w=s[0],s[1],s[2]
        cs={p for p in self.cells(L,T,w) if onb(p)}
        hit=[c for c,b in self.sw if cs & b]
        if len(set(hit))>1: return None
        if hit: return (L,T,w,hit[0],s[4],s[5])
        return s
    def bfs(self,start,goal,cap=8000000):
        prev={start:None}; q=collections.deque([start])
        while q:
            s=q.popleft()
            if goal(s):
                path=[]; cur=s
                while prev[cur]: cur,n=prev[cur]; path.append(n)
                return s,path[::-1]
            for name,d in MOVES:
                ns=self.step(s,d)
                if ns is None: continue
                ns=self.recolour(ns)
                if ns is None or ns in prev: continue
                prev[ns]=(s,name); q.append(ns)
            if len(prev)>cap: break
        return None,None
