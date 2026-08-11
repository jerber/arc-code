#!/usr/bin/env python3
"""Full pipeline: parse board -> boxes/swatches/shapes -> assignment -> routes."""
import parse, collections, itertools, route as R

BG='5'; FRAME='4'; ACTIVE='0'; BORDER='2'
W,H=64,63

def grid(idx=-1):
    bl=parse.load(); return bl[idx][0], bl[idx][1][-1][1]

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
    elif kind=='dline':
        for k in range(-r,r+1): s.add((k,k))
    elif kind=='aline':
        for k in range(-r,r+1): s.add((k,-k))
    elif kind=='fdiamond':
        for dx in range(-r,r+1):
            for dy in range(-r+abs(dx),r-abs(dx)+1): s.add((dx,dy))
    elif kind=='fsquare':
        for dx in range(-r,r+1):
            for dy in range(-r,r+1): s.add((dx,dy))
    elif kind=='hbar3':
        for k in range(-r,r+1):
            for j in(-1,0,1): s.add((k,j))
    return s
KINDS=['plus','X','diamond','square','hline','vline','dline','aline','fdiamond','fsquare']

def boxes_of(g):
    out=[]
    for y in range(1,H-1):
        for x in range(1,W-1):
            ring=[(x+dx,y+dy) for dx in(-1,0,1) for dy in(-1,0,1) if (dx,dy)!=(0,0)]
            if sum(1 for a,b in ring if g[b][a]==FRAME)>=5 and g[y][x] not in (BG,FRAME):
                out.append((x,y,g[y][x]))
    return out

def parse_board(idx=-1):
    h,g=grid(idx)
    bx=boxes_of(g); boxcells={(x,y) for x,y,c in bx}
    sw=R.swatches(g); swcells=set()
    for c,cells in sw: swcells|=cells
    # also drop the '2' borders
    ALL=set(); bycol=collections.defaultdict(set); marker=None
    for y in range(H):
        for x in range(W):
            c=g[y][x]
            if c in (BG,FRAME,BORDER): continue
            if (x,y) in boxcells or (x,y) in swcells: continue
            ALL.add((x,y))
            if c==ACTIVE: marker=(x,y)
            else: bycol[c].add((x,y))
    return dict(header=h,g=g,boxes=bx,boxcells=boxcells,sw=sw,swcells=swcells,
                ALL=ALL,bycol=bycol,marker=marker)

def find_prims(S, ALL, minsize=8):
    cands=[]
    xs=[p[0] for p in S]; ys=[p[1] for p in S]
    for cx in range(min(xs)-2,max(xs)+3):
        for cy in range(min(ys)-2,max(ys)+3):
            for kind in KINDS:
                r=1; best=None
                while r<=45:
                    cells={(cx+a,cy+b) for a,b in fam(kind,r)}
                    onb={p for p in cells if 0<=p[0]<W and 0<=p[1]<H}
                    if not onb or not onb<=ALL: break
                    if len(onb)>=minsize and sum(1 for p in onb if p in S)>=0.9*len(onb):
                        best=(kind,(cx,cy),r,frozenset(onb))
                    r+=1
                if best: cands.append(best)
    cands.sort(key=lambda c:-len(c[3]))
    keep=[]
    for c in cands:
        if not any(c[3]<=k[3] for k in keep): keep.append(c)
    return keep

def decompose(st, verbose=True):
    """returns list of (colour, kind, centre, r, cells)"""
    shapes=[]
    for col,S in st['bycol'].items():
        Sx=set(S)
        if st['marker']: Sx.add(st['marker'])
        prims=find_prims(Sx, st['ALL'])
        sel=None
        for n in range(1,5):
            for combo in itertools.combinations(prims[:16],n):
                u=set()
                for p in combo: u|=p[3]
                if S<=u: sel=combo; break
            if sel: break
        if sel is None:
            if verbose: print(f" !! colour {col}: no decomposition, {len(S)} cells; prims {[(k,c,r,len(cl)) for k,c,r,cl in prims[:8]]}")
            continue
        for kind,c,r,cells in sel: shapes.append((col,kind,c,r,cells))
    return shapes

def report(idx=-1):
    st=parse_board(idx)
    print(st['header'])
    print("marker",st['marker'])
    print("swatches",[(c,min(cells)) for c,cells in st['sw']])
    bb=collections.defaultdict(list)
    for x,y,c in st['boxes']: bb[c].append((x,y))
    print("boxes",{k:sorted(v) for k,v in bb.items()})
    sh=decompose(st)
    for col,kind,c,r,cells in sh: print(f"shape col={col} {kind} c={c} r={r} n={len(cells)}")
    return st,sh
if __name__=="__main__":
    report()
