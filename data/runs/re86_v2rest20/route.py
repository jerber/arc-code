#!/usr/bin/env python3
"""BFS route a shape from (centre,colour) to (target centre,target colour),
picking up colours by overlapping palette swatches, avoiding wrong ones."""
import collections, parse, auto

def swatches(g):
    """return list of (colour, set_of_cells) for 4x4 blocks framed by '2'."""
    out=[]
    seen=set()
    for y in range(63):
        for x in range(64):
            c=g[y][x]
            if c in ('5','4','2','0') or (x,y) in seen: continue
            # flood 4-connected same colour
            st=[(x,y)]; comp=set([(x,y)]); seen.add((x,y))
            while st:
                cx,cy=st.pop()
                for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=cx+dx,cy+dy
                    if 0<=nx<64 and 0<=ny<63 and (nx,ny) not in comp and g[ny][nx]==c:
                        comp.add((nx,ny)); seen.add((nx,ny)); st.append((nx,ny))
            xs=[p[0] for p in comp]; ys=[p[1] for p in comp]
            if len(comp)==16 and max(xs)-min(xs)==3 and max(ys)-min(ys)==3:
                # check border is '2'
                ok=all(g[b][a]=='2' for a in range(min(xs)-1,max(xs)+2) for b in (min(ys)-1,max(ys)+1) if 0<=a<64) 
                if ok: out.append((c,comp))
    return out

MOVES={'ACTION1':(0,-3),'ACTION2':(0,3),'ACTION3':(-3,0),'ACTION4':(3,0)}

def route(offs, start, startcol, target, targetcol, sw, lo=0, hi=63):
    """offs: shape offsets; sw: list (colour,cells). BFS over (centre,colour)."""
    swl=[(c,cells) for c,cells in sw]
    def colour_at(c, cur):
        for col,cells in swl:
            if any((c[0]+a,c[1]+b) in cells for a,b in offs): return col
        return cur
    start_state=(start,colour_at(start,startcol))
    q=collections.deque([start_state]); prev={start_state:None}
    goal=(target,targetcol)
    while q:
        s=q.popleft()
        if s==goal: break
        (cx,cy),col=s
        for name,(dx,dy) in MOVES.items():
            n=(cx+dx,cy+dy)
            if not (lo<=n[0]<=hi and lo<=n[1]<=hi): continue
            ns=(n,colour_at(n,col))
            if ns in prev: continue
            prev[ns]=(s,name); q.append(ns)
    if goal not in prev: return None
    path=[]; s=goal
    while prev[s]: s,name=prev[s]; path.append(name)
    return path[::-1]
