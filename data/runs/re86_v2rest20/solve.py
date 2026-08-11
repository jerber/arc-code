#!/usr/bin/env python3
"""Fit each coloured shape to a canonical family, find target centre covering its boxes."""
import parse, collections, sys

BG='5'; FRAME='4'; ACTIVE='0'

def load_grid(idx=-1):
    bl=parse.load(); return bl[idx][0], bl[idx][1][-1][1]

def find_boxes(g):
    boxes=[]
    for y in range(1,62):
        for x in range(1,63):
            ring=[(x+dx,y+dy) for dx in(-1,0,1) for dy in(-1,0,1) if (dx,dy)!=(0,0)]
            nf=sum(1 for (a,b) in ring if g[b][a]==FRAME)
            c=g[y][x]
            if nf>=5 and c not in (BG,FRAME): boxes.append((x,y,c))
    return boxes

def fam_set(kind,r):
    s=set()
    if kind=='plus':
        for k in range(-r,r+1): s.add((k,0)); s.add((0,k))
    elif kind=='X':
        for k in range(-r,r+1): s.add((k,k)); s.add((k,-k))
    elif kind=='diamond':
        for dx in range(-r,r+1):
            dy=r-abs(dx); s.add((dx,dy)); s.add((dx,-dy))
    elif kind=='square':
        for k in range(-r,r+1):
            s.add((k,-r)); s.add((k,r)); s.add((-r,k)); s.add((r,k))
    elif kind=='fdiamond':
        for dx in range(-r,r+1):
            for dy in range(-r,r+1):
                if abs(dx)+abs(dy)<=r: s.add((dx,dy))
    elif kind=='fsquare':
        for dx in range(-r,r+1):
            for dy in range(-r,r+1): s.add((dx,dy))
    return s

KINDS=['plus','X','diamond','square','fdiamond','fsquare']

def fit(cells):
    """return (kind, center, r, coverage) best fit"""
    xs=[c[0] for c in cells]; ys=[c[1] for c in cells]
    S=set(cells); best=None
    for cx in range(min(xs)-1,max(xs)+2):
        for cy in range(min(ys)-1,max(ys)+2):
            offs=[(x-cx,y-cy) for x,y in cells]
            for kind in KINDS:
                if kind=='plus': r=max((max(abs(a),abs(b)) for a,b in offs))
                elif kind=='X': r=max((max(abs(a),abs(b)) for a,b in offs))
                elif kind=='diamond': r=max(abs(a)+abs(b) for a,b in offs)
                elif kind=='square': r=max(max(abs(a),abs(b)) for a,b in offs)
                elif kind=='fdiamond': r=max(abs(a)+abs(b) for a,b in offs)
                else: r=max(max(abs(a),abs(b)) for a,b in offs)
                fs=fam_set(kind,r)
                if not all(o in fs for o in offs): continue
                onboard=[(cx+a,cy+b) for a,b in fs if 0<=cx+a<64 and 0<=cy+b<63]
                if not onboard: continue
                cov=sum(1 for p in onboard if p in S)/len(onboard)
                cand=(cov,-r,kind,(cx,cy),r)
                if best is None or cand>best: best=cand
    cov,_,kind,c,r=best
    return kind,c,r,cov

def analyse(idx=-1, verbose=True):
    h,g=load_grid(idx)
    boxes=find_boxes(g)
    boxby=collections.defaultdict(list); boxcells=set()
    for x,y,c in boxes: boxby[c].append((x,y)); boxcells.add((x,y))
    colcells=collections.defaultdict(list); active=None
    for y in range(63):
        for x in range(64):
            c=g[y][x]
            if c in (BG,FRAME) or (x,y) in boxcells: continue
            if c==ACTIVE: active=(x,y); continue
            colcells[c].append((x,y))
    actcol=None
    if active:
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                nx,ny=active[0]+dx,active[1]+dy
                if 0<=nx<64 and 0<=ny<63 and (nx,ny) not in boxcells and g[ny][nx] not in (BG,FRAME,ACTIVE):
                    actcol=g[ny][nx]; break
            if actcol: break
        if actcol: colcells[actcol].append(active)
    out={}
    if verbose: print(h, "| active", active, actcol, "| bar", sum(1 for ch in g[63] if ch!='f'))
    for col,cells in sorted(colcells.items()):
        if len(cells)<4: continue
        kind,c,r,cov=fit(cells)
        tg=targets(kind,c,r,boxby.get(col,[]))
        out[col]=dict(kind=kind,center=c,r=r,n=len(cells),cov=round(cov,2),boxes=sorted(boxby.get(col,[])),targets=tg,active=(col==actcol))
        if verbose:
            print(f"  col={col} kind={kind} c={c} r={r} n={len(cells)} cov={cov:.2f} boxes={sorted(boxby.get(col,[]))} targets={tg}")
    return out

def targets(kind,c,r,boxes):
    if not boxes: return []
    fs=fam_set(kind,r); res=[]
    for tx in range(64):
        for ty in range(63):
            if (tx-c[0])%3 or (ty-c[1])%3: continue
            if all((bx-tx,by-ty) in fs for bx,by in boxes): res.append((tx,ty))
    return res

def plan(c,t):
    dx=(t[0]-c[0])//3; dy=(t[1]-c[1])//3
    a=[]
    a += ['ACTION4']*dx if dx>0 else ['ACTION3']*(-dx)
    a += ['ACTION2']*dy if dy>0 else ['ACTION1']*(-dy)
    return a

if __name__=="__main__":
    info=analyse()
    for col,d in info.items():
        if d['targets']:
            for t in d['targets'][:3]:
                print(f"  plan {col} -> {t}: {len(plan(d['center'],t))} moves: {' '.join(plan(d['center'],t))}")
