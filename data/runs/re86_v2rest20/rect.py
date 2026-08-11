#!/usr/bin/env python3
"""Planner for rectangle-ring shapes with conserved size budget, obstacles and swatches."""
import collections, sim

MOVES=[('ACTION1',(0,-3)),('ACTION2',(0,3)),('ACTION3',(-3,0)),('ACTION4',(3,0))]
W,H=64,63

def onb(p): return 0<=p[0]<W and 0<=p[1]<H

class Game:
    def __init__(self, obst, swatches, budget):
        self.obst=obst; self.sw=swatches; self.budget=budget
    def cells(self,L,T,w):
        h=self.budget-w; R=L+w-1; B=T+h-1
        s=set()
        for x in range(L,R+1): s.add((x,T)); s.add((x,B))
        for y in range(T,B+1): s.add((L,y)); s.add((R,y))
        return s
    def hit(self,cells):
        return any(onb(p) and p in self.obst for p in cells)
    def vline(self,x,T,B): return {(x,y) for y in range(T,B+1)}
    def hline(self,y,L,R): return {(x,y) for x in range(L,R+1)}
    def step(self,state,d):
        L,T,w,col,vg,hg=state
        h=self.budget-w; R=L+w-1; B=T+h-1
        dx,dy=d
        if dx:
            lead = R if dx>0 else L
            trail = L if dx>0 else R
            bl=self.hit(self.vline(lead+dx,T,B))
            bt=self.hit(self.vline(trail+dx,T,B))
            bh=self.hit(self.hline(T,L+dx,R+dx)) or self.hit(self.hline(B,L+dx,R+dx))
            if bh or bt: return None
            if bl:
                if w-3<1: return None
                nw=w-3
                if dx>0: nL=L+3
                else:    nL=L
                # perpendicular grows by 3
                if vg==0: nT=T-3
                else:     nT=T
                return (nL,nT,nw,col,1-vg,hg)
            return (L+dx,T,w,col,vg,hg)
        else:
            lead = B if dy>0 else T
            trail = T if dy>0 else B
            bl=self.hit(self.hline(lead+dy,L,R))
            bt=self.hit(self.hline(trail+dy,L,R))
            bv=self.hit(self.vline(L,T+dy,B+dy)) or self.hit(self.vline(R,T+dy,B+dy))
            if bv or bt: return None
            if bl:
                if self.budget-w-3<1: return None
                nw=w+3
                if dy>0: nT=T+3
                else:    nT=T
                if hg==0: nL=L-3
                else:     nL=L
                return (nL,nT,nw,col,vg,1-hg)
            return (L,T+dy,w,col,vg,hg)
    def recolour(self,state):
        L,T,w,col,vg,hg=state
        cs={p for p in self.cells(L,T,w) if onb(p)}
        hits=[c for c,b in self.sw if cs & b]
        if len(set(hits))>1: return None      # ambiguous -> forbid
        if hits: return (L,T,w,hits[0],vg,hg)
        return state
    def bfs(self,start,goal_fn,lo=-36,hi=69,cap=3000000):
        prev={start:None}; q=collections.deque([start])
        while q:
            s=q.popleft()
            if goal_fn(s):
                path=[]; cur=s
                while prev[cur]: cur,n=prev[cur]; path.append(n)
                return s,path[::-1]
            for name,d in MOVES:
                ns=self.step(s,d)
                if ns is None: continue
                if not (lo<=ns[0]<=hi and lo<=ns[1]<=hi): continue
                ns=self.recolour(ns)
                if ns is None or ns in prev: continue
                prev[ns]=(s,name); q.append(ns)
            if len(prev)>cap: break
        return None,None
