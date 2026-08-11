import world,heapq,sys
from collections import defaultdict
TRACK=set('5bcef7023')   # pixels that can sit on a track (incl. carts drawn over it)

def extract(w=None):
    if w is None: w=world.build()
    off=w['off']; fl=w['fl']
    canvas={}
    for f,o in zip(fl,w['offs']):
        for y in range(1,64):
            for x in range(64): canvas[(x+o[0],y+o[1])]=f['rows'][y][x]
    cells=dict(w['world_cells'])
    if not cells: return None
    px,py=sorted(cells)[0][0]%6, sorted(cells)[0][1]%6
    rows=fl[-1]['rows']
    # --- objects in the CURRENT frame: shuttles (c/e core) and pivot-carts (f core, b ring)
    carts={}
    for y in range(0,61):
        for x in range(0,61):
            if (x+off[0]-px)%6 or (y+off[1]-py)%6: continue
            blk=''.join(rows[y+dy][x:x+4] for dy in range(4))
            ring=[]
            for i in range(-1,5):
                if y-1>=0 and 0<=x+i<64: ring.append(rows[y-1][x+i])
                if y+4<64 and 0<=x+i<64: ring.append(rows[y+4][x+i])
            for dy in range(4):
                if x-1>=0: ring.append(rows[y+dy][x-1])
                if x+4<64: ring.append(rows[y+dy][x+4])
            sides=[rows[y+dy][x-1] for dy in range(4) if x-1>=0]+[rows[y+dy][x+4] for dy in range(4) if x+4<64]
            if all(ch in 'ce' for ch in blk) and 'c' in blk and all(ch=='b' for ch in ring):
                carts[(x+off[0],y+off[1])]=('S','P' if 'e' in blk else '.')
            elif set(blk)<=set('f705') and 'f' in blk and len(sides)==8 and all(ch=='b' for ch in sides):
                carts[(x+off[0],y+off[1])]=('V','.')
    # --- static pivots (purple, no b ring) anywhere in canvas
    cnt=defaultdict(int)
    for (x,y),v in canvas.items():
        if v!='f': continue
        cx=x-((x-px)%6); cy=y-((y-py)%6)
        if (x-cx)<4 and (y-cy)<4: cnt[(cx,cy)]+=1
    pivots=set(k for k,v in cnt.items() if v>=5)
    pivots-=set(carts)
    reds=set(k for k,v in cells.items() if v=='R')
    for k in reds: cells[k]='.'
    pivots-=set(cells)
    # --- track nodes and edges
    def tp(p): return canvas.get(p,'?') in TRACK
    nodes=set()
    xs=[p[0] for p in canvas]; ys=[p[1] for p in canvas]
    x0=min(xs)-((min(xs)-px)%6); y0=min(ys)-((min(ys)-py)%6)
    for y in range(y0,max(ys)+1,6):
        for x in range(x0,max(xs)+1,6):
            if (x,y) in cells or (x,y) in pivots: continue
            if all(tp((x+dx,y+dy)) for dx in (1,2) for dy in (1,2)): nodes.add((x,y))
    nodes|=set(carts)
    edges=defaultdict(set)
    for (x,y) in nodes:
        for q in ((x+6,y),(x,y+6)):
            if q not in nodes: continue
            if q[0]!=x:
                ok=all(tp((xx,y+s)) for xx in range(x+1,x+9) for s in (1,2))
            else:
                ok=all(tp((x+s,yy)) for yy in range(y+1,y+9) for s in (1,2))
            if ok:
                edges[(x,y)].add(q); edges[q].add((x,y))
    E=dict(cells=cells,pivots=pivots,reds=reds,nodes=nodes,edges=edges,carts=carts,canvas=canvas,
                off=off,phase=(px,py),w=w)
    E['carts']=track_carts(E)
    pivots-=set(E['carts'])
    return E

def detect_carts(rows,off,px,py):
    out={}
    for y in range(0,61):
        for x in range(0,61):
            if (x+off[0]-px)%6 or (y+off[1]-py)%6: continue
            blk=''.join(rows[y+dy][x:x+4] for dy in range(4))
            ring=[]
            for i in range(-1,5):
                if y-1>=0 and 0<=x+i<64: ring.append(rows[y-1][x+i])
                if y+4<64 and 0<=x+i<64: ring.append(rows[y+4][x+i])
            for dy in range(4):
                if x-1>=0: ring.append(rows[y+dy][x-1])
                if x+4<64: ring.append(rows[y+dy][x+4])
            sides=[rows[y+dy][x-1] for dy in range(4) if x-1>=0]+[rows[y+dy][x+4] for dy in range(4) if x+4<64]
            if all(ch in 'ce' for ch in blk) and 'c' in blk and all(ch=='b' for ch in ring):
                out[(x+off[0],y+off[1])]=('S','P' if 'e' in blk else '.')
            elif set(blk)<=set('f705') and 'f' in blk and len(sides)==8 and all(ch=='b' for ch in sides):
                out[(x+off[0],y+off[1])]=('V','.')
    return out

def track_carts(E):
    w=E['w']; fl=w['fl']; offs=w['offs']; px,py=E['phase']; edges=E['edges']
    tracked={}
    for i,(f,o) in enumerate(zip(fl,offs)):
        det=detect_carts(f['rows'],o,px,py)
        if i>0:
            what=f['what']
            d=None
            for dd,nm in DIRNAME.items():
                if what.startswith(nm): d=dd
            if d is not None and tracked:
                keys=sorted(tracked)
                kinds=tuple(tracked[k][0] for k in keys)
                newpos=move_carts(tuple(keys),kinds,d,edges)
                tracked={newpos[j]:tracked[keys[j]] for j in range(len(keys))}
        # observations override in visible region (with margin)
        x0,y0=o
        for k in list(tracked):
            if x0+2<=k[0]<=x0+56 and y0+2<=k[1]<=y0+56 and k not in det:
                del tracked[k]
        tracked.update(det)
    return tracked


DIRS=[(6,0),(-6,0),(0,6),(0,-6)]
DIRNAME={(0,-6):'ACTION1',(0,6):'ACTION2',(-6,0):'ACTION3',(6,0):'ACTION4'}

def move_carts(pos,kinds,d,edges):
    """simultaneous move; returns new positions tuple"""
    n=len(pos); new=list(pos); moved=[False]*n
    for _ in range(n):
        changed=False
        occ=set(new)
        for i in range(n):
            if moved[i]: continue
            q=(new[i][0]+d[0],new[i][1]+d[1])
            if q in edges[new[i]] and q not in occ:
                occ.discard(new[i]); occ.add(q); new[i]=q; moved[i]=True; changed=True
        if not changed: break
    return tuple(new)

def solve(E,maxexp=600000,verbose=True):
    cells=E['cells']; pivots=E['pivots']; edges=E['edges']; reds0=frozenset(E.get('reds',()))
    carts=sorted(E['carts'].items())
    kinds=tuple(v[0] for k,v in carts)
    pos0=tuple(k for k,v in carts)
    load0=tuple(v[1]=='P' for k,v in carts)
    pegs0=frozenset(k for k,v in cells.items() if v=='P')
    holes=set(cells)
    start=(pegs0,reds0,pos0,load0)
    def npegs(st): return len(st[0])+sum(st[3])
    def won(st): return len(st[0])==1   # exactly one green peg sitting on a board cell
    def succ(st):
        pegs,reds,pos,load=st
        out=[]
        for d in DIRS:
            np_=move_carts(pos,kinds,d,edges)
            if np_!=pos: out.append(((pegs,reds,np_,load),(DIRNAME[d],)))
        occ=set(pegs)|set(pivots)|set(reds)
        land=set(holes)-set(reds)
        for i,p_ in enumerate(pos):
            if kinds[i]=='V': occ.add(p_)
            else:
                land.add(p_)
                if load[i]: occ.add(p_)
        movers=[(a,'peg') for a in pegs]+[(a,'red') for a in reds]  # reds may land in shuttles
        movers+=[(p_,'shut%d'%i) for i,p_ in enumerate(pos) if kinds[i]=='S' and load[i]]
        for a,typ in movers:
            for d in DIRS:
                b=(a[0]+d[0],a[1]+d[1]); c=(a[0]+2*d[0],a[1]+2*d[1])
                if b not in occ or c not in land or c in occ: continue
                pg=set(pegs); rd=set(reds); ld=list(load)
                # remove mover from source
                if typ=='peg': pg.discard(a)
                elif typ=='red': rd.discard(a)
                else: ld[int(typ[4:])]=False
                # only a GREEN mover consumes what it jumps over (verified in L6)
                if typ!='red':
                    if b in pg: pg.discard(b)
                    else:
                        for i,pp in enumerate(pos):
                            if pp==b and kinds[i]=='S' and ld[i]: ld[i]=False; break
                # place mover at c
                if typ=='red':
                    inshut=False
                    for i,pp in enumerate(pos):
                        if pp==c and kinds[i]=='S': inshut=True; break
                    if not inshut: rd.add(c)
                else:
                    placed=False
                    for i,pp in enumerate(pos):
                        if pp==c and kinds[i]=='S': ld[i]=True; placed=True; break
                    if not placed: pg.add(c)
                out.append(((frozenset(pg),frozenset(rd),pos,tuple(ld)),('JUMP',a,b,c)))
        return out
    h=lambda st: 2*max(0,len(st[0])-1)
    pq=[(h(start),0,0,start,[])]; best={start:0}; cnt=0; exp=0
    while pq:
        f,g,_,st,path=heapq.heappop(pq)
        if won(st): return path
        if g>best.get(st,1e9): continue
        exp+=1
        if exp>maxexp:
            if verbose: print('search gave up after',exp)
            return None
        for nst,mv in succ(st):
            ng=g+(2 if mv[0]=='JUMP' else 1)
            if ng<best.get(nst,1e9):
                best[nst]=ng; cnt+=1
                heapq.heappush(pq,(ng+h(nst),ng,cnt,nst,path+[mv]))
    return None

def dump(E):
    c=E['cells']
    print('CELLS:')
    for y in sorted(set(p[1] for p in c)): print(' y=%d:'%y, ' '.join('%d%s'%(x,c[(x,y)]) for x in sorted(p[0] for p in c if p[1]==y)))
    print('PIVOTS:',sorted(E['pivots']),'REDS:',sorted(E.get('reds',())))
    print('CARTS:',sorted(E['carts'].items()))
    n=E['nodes']
    print('NODES:')
    for y in sorted(set(p[1] for p in n)): print(' y=%d:'%y, sorted(x for x,yy in n if yy==y))
    print('off',E['off'])
if __name__=='__main__':
    E=extract(); dump(E)
    if '-s' in sys.argv:
        r=solve(E)
        print('SOLUTION' if r else 'NO SOLUTION')
        if r:
            for m in r: print('  ',m)
