"""General planner: Dijkstra over (pegs, shuttle positions, shuttle loads) -> 1 peg."""
import json, heapq, collections, itertools, sys
S=json.load(open('structure.json'))
CELLS={tuple(x) for x in S['cells']}; PIVOTS={tuple(x) for x in S['pivots']}
TRACK={tuple(x) for x in S['track']}
CONN={((a,b),(c,d)) for a,b,c,d in S['conn']}
TCONN={((a,b),(c,d)) for a,b,c,d in S['tconn']}
DIRS={'ACTION1':(0,-1),'ACTION2':(0,1),'ACTION3':(-1,0),'ACTION4':(1,0)}
def linked(a,b):
    """can a jump line pass between lattice-adjacent a,b?"""
    if abs(a[0]-b[0])+abs(a[1]-b[1])!=1: return False
    if a in TRACK or b in TRACK: return True          # shuttle dock adjacency
    return (a,b) in CONN
def moves_of_shuttles(pos,d):
    """pos: tuple of shuttle cells; returns new tuple after pressing direction d"""
    new=list(pos); moved=[False]*len(pos)
    for _ in range(len(pos)):
        changed=False
        for i,p in enumerate(new):
            if moved[i]: continue
            t=(p[0]+d[0],p[1]+d[1])
            if t in TRACK and (p,t) in TCONN and t not in set(new):
                new[i]=t; moved[i]=True; changed=True
        if not changed: break
    return tuple(new)
def jumps(pegs,pos,load):
    """yield (kind, A, M, L, newpegs, newload) ; A/L may be shuttle cells"""
    out=[]
    shat={p:i for i,p in enumerate(pos)}
    # peg sources: cells with pegs, or loaded shuttles
    srcs=[(p,None) for p in pegs]+[(pos[i],i) for i in range(len(pos)) if load[i]=='peg']
    for A,si in srcs:
        for d in ((1,0),(-1,0),(0,1),(0,-1)):
            M=(A[0]+d[0],A[1]+d[1]); L=(A[0]+2*d[0],A[1]+2*d[1])
            if not linked(A,M) or not linked(M,L): continue
            # middle must be occupied: peg, pivot, or loaded shuttle
            midok = (M in pegs) or (M in PIVOTS) or (M in shat and load[shat[M]] is not None)
            if not midok: continue
            # landing must be empty cell or empty shuttle
            if L in CELLS and L not in pegs and L not in shat: kindL='cell'
            elif L in shat and load[shat[L]] is None: kindL='sh'
            else: continue
            np=set(pegs); nl=list(load)
            if si is None: np.discard(A)
            else: nl[si]=None
            if M in np: np.discard(M)
            elif M in shat and load[shat[M]]=='peg': nl[shat[M]]=None
            if kindL=='cell': np.add(L)
            else: nl[shat[L]]='peg'
            out.append((A,M,L,frozenset(np),tuple(nl)))
    return out
def plan(pegs,pos,load,maxstates=400000,verbose=True):
    start=(frozenset(pegs),tuple(pos),tuple(load))
    dist={start:0}; prev={}
    pq=[(0,start)]
    goal=None
    while pq:
        d,st=heapq.heappop(pq)
        if d>dist.get(st,1e9): continue
        pegs_,pos_,load_=st
        if len(pegs_)+sum(1 for x in load_ if x=='peg')==1: goal=st; break
        if len(dist)>maxstates: break
        for name,dd in DIRS.items():
            npos=moves_of_shuttles(pos_,dd)
            if npos==pos_: continue
            ns=(pegs_,npos,load_); nd=d+1
            if nd<dist.get(ns,1e9): dist[ns]=nd; prev[ns]=(st,('press',name)); heapq.heappush(pq,(nd,ns))
        for A,M,L,np_,nl in jumps(pegs_,pos_,load_):
            ns=(np_,pos_,nl); nd=d+2
            if nd<dist.get(ns,1e9): dist[ns]=nd; prev[ns]=(st,('jump',A,M,L)); heapq.heappush(pq,(nd,ns))
    if goal is None:
        if verbose: print('no plan found; states',len(dist))
        return None
    seq=[]; st=goal
    while st in prev:
        st,mv=prev[st]; seq.append(mv)
    seq.reverse()
    if verbose: print('plan cost',dist[goal],'actions; states explored',len(dist))
    return seq
