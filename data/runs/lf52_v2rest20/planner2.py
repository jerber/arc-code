"""Planner with greens, reds (mobile pivots), pivots, shuttles. Goal: 1 green peg."""
import json, heapq, collections
S=json.load(open('structure.json'))
CELLS={tuple(x) for x in S['cells']}; PIVOTS={tuple(x) for x in S['pivots']}
TRACK={tuple(x) for x in S['track']}
CONN={((a,b),(c,d)) for a,b,c,d in S['conn']}
TCONN={((a,b),(c,d)) for a,b,c,d in S['tconn']}
DIRS={'ACTION1':(0,-1),'ACTION2':(0,1),'ACTION3':(-1,0),'ACTION4':(1,0)}
def linked(a,b):
    if abs(a[0]-b[0])+abs(a[1]-b[1])!=1: return False
    if a in TRACK or b in TRACK: return True
    return (a,b) in CONN
def shuttle_move(pos,d):
    new=list(pos); moved=[False]*len(pos)
    for _ in range(len(pos)):
        ch=False
        for i,p in enumerate(new):
            if moved[i]: continue
            t=(p[0]+d[0],p[1]+d[1])
            if t in TRACK and (p,t) in TCONN and t not in set(new):
                new[i]=t; moved[i]=True; ch=True
        if not ch: break
    return tuple(new)
def jumps(g,r,pos,cargo):
    out=[]; shat={p:i for i,p in enumerate(pos)}
    srcs=[(p,'g',None) for p in g]+[(p,'r',None) for p in r]+ \
         [(pos[i],('g' if cargo[i]=='peg' else 'r'),i) for i in range(len(pos)) if cargo[i] in ('peg','red')]
    for A,kind,si in srcs:
        for d in ((1,0),(-1,0),(0,1),(0,-1)):
            M=(A[0]+d[0],A[1]+d[1]); L=(A[0]+2*d[0],A[1]+2*d[1])
            if not linked(A,M) or not linked(M,L): continue
            mi=shat.get(M)
            mid_green = (M in g) or (mi is not None and cargo[mi]=='peg')
            mid_solid = mid_green or (M in r) or (M in PIVOTS) or (mi is not None and cargo[mi] in ('red','pivot'))
            if not mid_solid: continue
            li=shat.get(L)
            if L in CELLS and L not in g and L not in r and L not in PIVOTS and li is None: kl='cell'
            elif li is not None and cargo[li] is None: kl='sh'
            else: continue
            ng=set(g); nr=set(r); nc=list(cargo)
            if si is None:
                (ng if kind=='g' else nr).discard(A)
            else: nc[si]=None
            if mid_green and kind=='g':
                if M in ng: ng.discard(M)
                else: nc[mi]=None
            if kl=='cell': (ng if kind=='g' else nr).add(L)
            else: nc[li]=('peg' if kind=='g' else 'red')
            out.append((A,M,L,frozenset(ng),frozenset(nr),tuple(nc)))
    return out
def plan(g,r,pos,cargo,maxstates=400000,verbose=True):
    start=(frozenset(g),frozenset(r),tuple(pos),tuple(cargo))
    dist={start:0}; prev={}; pq=[(0,0,start)]; cnt=1; goal=None
    def ngreen(st): return len(st[0])+sum(1 for c in st[3] if c=='peg')
    while pq:
        d,_,st=heapq.heappop(pq)
        if d>dist.get(st,1<<30): continue
        if ngreen(st)==1: goal=st; break
        if len(dist)>maxstates: break
        g_,r_,pos_,c_=st
        for nm,dd in DIRS.items():
            np_=shuttle_move(pos_,dd)
            if np_==pos_: continue
            ns=(g_,r_,np_,c_); nd=d+1
            if nd<dist.get(ns,1<<30):
                dist[ns]=nd; prev[ns]=(st,('press',nm)); cnt+=1; heapq.heappush(pq,(nd,cnt,ns))
        for A,M,L,ng,nr,nc in jumps(g_,r_,pos_,c_):
            ns=(ng,nr,pos_,nc); nd=d+2
            if nd<dist.get(ns,1<<30):
                dist[ns]=nd; prev[ns]=(st,('jump',A,M,L)); cnt+=1; heapq.heappush(pq,(nd,cnt,ns))
    if goal is None:
        if verbose: print('no plan; states',len(dist)); return None
    seq=[]; st=goal
    while st in prev: st,mv=prev[st]; seq.append(mv)
    seq.reverse()
    if verbose: print('plan cost',dist[goal],'actions; states',len(dist))
    return seq

def plan_goal(g,r,pos,cargo,goalfn,maxstates=300000,verbose=True):
    start=(frozenset(g),frozenset(r),tuple(pos),tuple(cargo))
    dist={start:0}; prev={}; pq=[(0,0,start)]; cnt=1; goal=None
    while pq:
        d,_,st=heapq.heappop(pq)
        if d>dist.get(st,1<<30): continue
        if goalfn(st): goal=st; break
        if len(dist)>maxstates: break
        g_,r_,pos_,c_=st
        for nm,dd in DIRS.items():
            np_=shuttle_move(pos_,dd)
            if np_==pos_: continue
            ns=(g_,r_,np_,c_); nd=d+1
            if nd<dist.get(ns,1<<30):
                dist[ns]=nd; prev[ns]=(st,('press',nm)); cnt+=1; heapq.heappush(pq,(nd,cnt,ns))
        for A,M,L,ng,nr,nc in jumps(g_,r_,pos_,c_):
            ns=(ng,nr,pos_,nc); nd=d+2
            if nd<dist.get(ns,1<<30):
                dist[ns]=nd; prev[ns]=(st,('jump',A,M,L)); cnt+=1; heapq.heappush(pq,(nd,cnt,ns))
    if goal is None:
        if verbose: print('no plan; states',len(dist)); return None
    seq=[]; st=goal
    while st in prev: st,mv=prev[st]; seq.append(mv)
    seq.reverse()
    if verbose: print('plan cost',dist[goal],'states',len(dist))
    return seq
