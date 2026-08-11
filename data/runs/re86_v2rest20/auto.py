#!/usr/bin/env python3
"""General solver: decompose board into boxes + primitive shapes, solve set-cover."""
import parse, collections, itertools

BG='5'; FRAME='4'; ACTIVE='0'
W,H=64,63

def grid(idx=-1):
    bl=parse.load(); return bl[idx][0], bl[idx][1][-1][1]

def boxes_of(g):
    out=[]
    for y in range(1,H-1):
        for x in range(1,W-1):
            ring=[(x+dx,y+dy) for dx in(-1,0,1) for dy in(-1,0,1) if (dx,dy)!=(0,0)]
            if sum(1 for a,b in ring if g[b][a]==FRAME)>=5 and g[y][x] not in (BG,FRAME):
                out.append((x,y,g[y][x]))
    return out

def fam(kind,r):
    s=set()
    if kind=='plus':
        for k in range(-r,r+1): s.add((k,0)); s.add((0,k))
    elif kind=='X':
        for k in range(-r,r+1): s.add((k,k)); s.add((k,-k))
    elif kind=='diamond':
        for dx in range(-r,r+1):
            d=r-abs(dx); s.add((dx,d)); s.add((dx,-d))
    elif kind=='square':
        for k in range(-r,r+1):
            s.add((k,-r)); s.add((k,r)); s.add((-r,k)); s.add((r,k))
    elif kind=='hline':
        for k in range(-r,r+1): s.add((k,0))
    elif kind=='vline':
        for k in range(-r,r+1): s.add((0,k))
    elif kind=='dline':      # '\' diagonal
        for k in range(-r,r+1): s.add((k,k))
    elif kind=='aline':      # '/' diagonal
        for k in range(-r,r+1): s.add((k,-k))
    elif kind=='fdiamond':
        for dx in range(-r,r+1):
            for dy in range(-r+abs(dx),r-abs(dx)+1): s.add((dx,dy))
    elif kind=='fsquare':
        for dx in range(-r,r+1):
            for dy in range(-r,r+1): s.add((dx,dy))
    return s

KINDS=['plus','X','diamond','square','hline','vline','dline','aline','fdiamond','fsquare']

def onboard(cells): return {(x,y) for x,y in cells if 0<=x<W and 0<=y<H}

def primitives(S, ALL, minsize=8):
    """maximal primitives whose on-board cells all lie in ALL and mostly in S."""
    cands=[]
    xs=[p[0] for p in S]; ys=[p[1] for p in S]
    for cx in range(min(xs)-1,max(xs)+2):
        for cy in range(min(ys)-1,max(ys)+2):
            for kind in KINDS:
                best=None
                r=1
                while r<=40:
                    cells=onboard({(cx+a,cy+b) for a,b in fam(kind,r)})
                    if not cells or not cells<=ALL: break
                    own=sum(1 for p in cells if p in S)
                    if own>=0.75*len(cells) and len(cells)>=minsize: best=(kind,(cx,cy),r,frozenset(cells))
                    r+=1
                if best: cands.append(best)
    # keep maximal (cell-set not subset of another)
    cands.sort(key=lambda c:-len(c[3]))
    keep=[]
    for c in cands:
        if not any(c[3]<=k[3] for k in keep): keep.append(c)
    return keep

def cover_exact(S, prims):
    """greedy+search: minimal set of prims whose union covers S (all of S)."""
    best=None
    prims=sorted(prims,key=lambda p:-len(p[3]&S))
    for n in range(1,5):
        for combo in itertools.combinations(prims[:14],n):
            u=set()
            for p in combo: u|=p[3]
            if S<=u: return list(combo)
    return None

def analyse(idx=-1,verbose=True):
    h,g=grid(idx)
    bx=boxes_of(g)
    boxcells={(x,y) for x,y,c in bx}
    boxby=collections.defaultdict(list)
    for x,y,c in bx: boxby[c].append((x,y))
    ALL=set(); bycol=collections.defaultdict(set); marker=None
    for y in range(H):
        for x in range(W):
            c=g[y][x]
            if c in (BG,FRAME) or (x,y) in boxcells: continue
            ALL.add((x,y))
            if c==ACTIVE: marker=(x,y)
            else: bycol[c].add((x,y))
    if marker: ALL.add(marker)
    if verbose:
        print(h)
        print("marker",marker,"boxes:",{k:sorted(v) for k,v in boxby.items()})
    shapes={}
    for col,S in bycol.items():
        Sx=set(S)
        if marker: Sx.add(marker)
        prims=primitives(Sx,ALL|{marker} if marker else ALL)
        sel=cover_exact(set(S),prims)
        shapes[col]=sel
        if verbose:
            print(f"colour {col}: {len(S)} cells ->")
            for kind,c,r,cells in (sel or []): print(f"   {kind} c={c} r={r} n={len(cells)}")
            if sel is None: print("   NO DECOMPOSITION; top prims:",[(k,c,r,len(cl)) for k,c,r,cl in prims[:6]])
    return g,boxby,shapes,marker
if __name__=="__main__":
    analyse()
