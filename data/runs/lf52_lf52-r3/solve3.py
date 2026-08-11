import sys
from functools import lru_cache
CELLS=set()
for p in [(6,6),(12,6),(24,6),(30,6),(6,12),(12,12),(24,12),(30,12),
          (6,18),(12,18),(18,18),(24,18),(6,24),(12,24),(18,24),(24,24),
          (6,48),(12,48),(18,48),(24,48),(6,54),(12,54),(18,54),
          (66,6),(72,6),(60,12),(66,12),(72,12),(66,18),(72,18),(78,18),(84,18),
          (66,24),(72,24),(66,30),(72,30),(78,30),(84,30),(66,36),(72,36),
          (66,42),(72,42),(78,42),(66,48),(72,48),(66,54),(72,54)]:
    CELLS.add(p)
T1=[(36,12),(42,12),(48,12),(54,12)]
T2=[(30,48),(36,48),(42,48),(42,42),(42,36),(48,36),(54,36),(54,42),(54,48),(60,48)]
PEGS0=frozenset([(66,12),(72,18),(78,18),(72,30),(78,30),(66,42),(72,48),(12,48),(24,48)])
DIRS=[(6,0),(-6,0),(0,6),(0,-6)]

def moves(pegs,c1,c2):
    out=[]
    for s1 in T1:
        for s2 in T2:
            holes=CELLS|{s1,s2}
            occ=set(pegs)
            if c1: occ.add(s1)
            if c2: occ.add(s2)
            for a in list(occ):
                for d in DIRS:
                    b=(a[0]+d[0],a[1]+d[1]); c=(a[0]+2*d[0],a[1]+2*d[1])
                    if b not in holes or c not in holes: continue
                    if b not in occ or c in occ: continue
                    np=set(pegs); n1=c1; n2=c2
                    for q in (a,b):
                        if q==s1 and n1: n1=False
                        elif q==s2 and n2: n2=False
                        else: np.discard(q)
                    if c==s1: n1=True
                    elif c==s2: n2=True
                    else: np.add(c)
                    out.append(((frozenset(np),n1,n2),(a,b,c,s1,s2)))
    # dedup by resulting state, keep first
    seen={}
    for st,mv in out:
        if st not in seen: seen[st]=mv
    return list(seen.items())

def total(st): return len(st[0])+st[1]+st[2]

def solve():
    start=(PEGS0,False,False)
    import heapq
    seen={start:None}
    stack=[(start,[])]
    best=None
    # DFS
    sys.setrecursionlimit(10000)
    def dfs(st,path,visited):
        if total(st)==1: return path
        for nst,mv in moves(*st):
            if nst in visited: continue
            visited.add(nst)
            r=dfs(nst,path+[mv],visited)
            if r: return r
            visited.discard(nst)
        return None
    return dfs(start,[],{start})

if __name__=='__main__':
    r=solve()
    if r:
        print('SOLUTION',len(r),'jumps')
        for a,b,c,s1,s2 in r: print('  jump',a,'over',b,'->',c,' s1',s1,'s2',s2)
    else: print('no solution')
