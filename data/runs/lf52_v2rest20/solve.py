import parse, collections, sys, itertools

def grid(rows): return [[int(c,16) for c in r] for r in rows]

TILEVALS={1,0xe,2}   # empty, peg, highlighted-corner
def find_tiles(g):
    seen=set(); comps=[]
    for y in range(64):
        for x in range(64):
            if g[y][x] in TILEVALS and (x,y) not in seen:
                st=[(x,y)];comp=[];seen.add((x,y))
                while st:
                    cx,cy=st.pop();comp.append((cx,cy))
                    for dx in(-1,0,1):
                        for dy in(-1,0,1):
                            nx,ny=cx+dx,cy+dy
                            if 0<=nx<64 and 0<=ny<64 and (nx,ny) not in seen and g[ny][nx] in TILEVALS:
                                seen.add((nx,ny));st.append((nx,ny))
                xs=[p[0] for p in comp]; ys=[p[1] for p in comp]
                w,h=max(xs)-min(xs)+1, max(ys)-min(ys)+1
                comps.append((min(xs),min(ys),w,h,len(comp)))
    return comps

def board(g, verbose=False):
    comps=find_tiles(g)
    bad=[c for c in comps if (c[2],c[3])!=(4,4)]
    if bad and verbose: print('WARN non-4x4 comps:',bad, file=sys.stderr)
    ts=[c for c in comps if (c[2],c[3])==(4,4)]
    xs=sorted({c[0] for c in ts}); ys=sorted({c[1] for c in ts})
    X0,Y0=xs[0],ys[0]
    for v in xs: assert (v-X0)%6==0,(xs,)
    for v in ys: assert (v-Y0)%6==0,(ys,)
    cells={}
    for x0,y0,_,_,_ in ts:
        c,r=(x0-X0)//6,(y0-Y0)//6
        cells[(c,r)] = (g[y0+1][x0+1]==0xe)
    return X0,Y0,cells

def px(X0,Y0,c,r): return (X0+6*c+1, Y0+6*r+1)

DIRS=[(1,0),(-1,0),(0,1),(0,-1)]
def moves(cellset,pegs):
    out=[]
    for (c,r) in pegs:
        for dx,dy in DIRS:
            m=(c+dx,r+dy); d=(c+2*dx,r+2*dy)
            if m in pegs and d in cellset and d not in pegs:
                out.append(((c,r),m,d))
    return out

def components(cellset):
    seen=set(); out=[]
    for cell in cellset:
        if cell in seen: continue
        st=[cell]; comp=set([cell]); seen.add(cell)
        while st:
            c,r=st.pop()
            for dx,dy in DIRS:
                n=(c+dx,r+dy)
                if n in cellset and n not in seen:
                    seen.add(n); comp.add(n); st.append(n)
        out.append(comp)
    return out

def solve_comp(cellset, pegs, target=1, limit=4_000_000):
    """DFS to reduce pegs to `target` count. returns list of moves or None"""
    cellset=frozenset(cellset)
    dead=set(); cnt=[0]
    def dfs(pegs, path):
        cnt[0]+=1
        if cnt[0]>limit: raise TimeoutError
        if len(pegs)<=target: return list(path)
        key=pegs
        if key in dead: return None
        mv=moves(cellset,pegs)
        for a,m,d in mv:
            np=frozenset((pegs-{a,m})|{d})
            path.append((a,m,d))
            r=dfs(np,path)
            if r is not None: return r
            path.pop()
        dead.add(key)
        return None
    try:
        return dfs(frozenset(pegs),[])
    except TimeoutError:
        return None

def actions_for(X0,Y0,mvs):
    acts=[]
    for a,m,d in mvs:
        acts.append('ACTION6:%d,%d'%px(X0,Y0,*a))
        acts.append('ACTION6:%d,%d'%px(X0,Y0,*d))
    return acts

def main():
    hdr,rows=parse.last()
    g=grid(rows)
    X0,Y0,cells=board(g,verbose=True)
    print(hdr)
    cellset=set(cells); pegs={k for k,v in cells.items() if v}
    W=max(c for c,r in cellset)+1; H=max(r for c,r in cellset)+1
    print('origin',X0,Y0,'cells',len(cellset),'pegs',len(pegs),'dims',W,H)
    for r in range(H):
        print(''.join('O' if (c,r) in pegs else ('.' if (c,r) in cellset else ' ') for c in range(W)))
    comps=components(cellset)
    print('components:',[ (len(c), len(c&pegs)) for c in comps])
    allmv=[]
    for comp in comps:
        p=comp&pegs
        if len(p)<=1: continue
        s=solve_comp(comp,p,1)
        if s is None:
            print('  no 1-peg solution for comp of size',len(comp),'pegs',sorted(p))
            for t in (2,3):
                s=solve_comp(comp,p,t)
                if s: print('   solvable to',t); break
        if s: allmv+=s
    print('moves:',allmv)
    print('ACTIONS:',' '.join(actions_for(X0,Y0,allmv)))
main()
