import game as G
from collections import deque
E=G.extract()
cells=E['cells']; pivots=E['pivots']; edges=E['edges']
carts=sorted(E['carts'].items()); kinds=tuple(v[0] for k,v in carts)
pos0=tuple(k for k,v in carts); load0=tuple(False for k in carts)
pegs0=frozenset(k for k,v in cells.items() if v=='P'); holes=set(cells); reds0=frozenset(E['reds'])
def succ(st):
    pegs,reds,pos,load=st; out=[]
    for d in G.DIRS:
        np_=G.move_carts(pos,kinds,d,edges)
        if np_!=pos: out.append(((pegs,reds,np_,load),G.DIRNAME[d]))
    occ=set(pegs)|set(pivots)|set(reds); land=set(holes)-set(reds)
    for i,p_ in enumerate(pos):
        if kinds[i]=='V': occ.add(p_)
        else:
            land.add(p_)
            if load[i]: occ.add(p_)
    movers=[(a,'peg') for a in pegs]+[(a,'red') for a in reds]+[(p_,'s%d'%i) for i,p_ in enumerate(pos) if kinds[i]=='S' and load[i]]
    for a,typ in movers:
        for d in G.DIRS:
            b=(a[0]+d[0],a[1]+d[1]); c=(a[0]+2*d[0],a[1]+2*d[1])
            if b not in occ or c not in land or c in occ: continue
            pg=set(pegs); rd=set(reds); ld=list(load)
            if typ=='peg': pg.discard(a)
            elif typ=='red': rd.discard(a)
            else: ld[int(typ[1:])]=False
            if typ!='red':
                if b in pg: pg.discard(b)
                else:
                    for i,pp in enumerate(pos):
                        if pp==b and kinds[i]=='S' and ld[i]: ld[i]=False; break
            ins=False
            for i,pp in enumerate(pos):
                if pp==c and kinds[i]=='S':
                    ins=True
                    if typ!='red': ld[i]=True
                    break
            if not ins:
                if typ=='red': rd.add(c)
                else: pg.add(c)
            out.append(((frozenset(pg),frozenset(rd),pos,tuple(ld)),('JUMP',a,b,c)))
    return out
start=(pegs0,reds0,pos0,load0)
par={start:None}; q=deque([start])
while q:
    s=q.popleft()
    for ns,mv in succ(s):
        if ns not in par: par[ns]=(s,mv); q.append(ns)
print('total states',len(par))
cands=[s for s in par if len(s[0])==1 and sum(s[3])==0 and len(s[1])==0]
print('goal states (1 green on board, red parked):',len(cands))
for s in cands[:3]:
    path=[]; cur=s
    while par[cur]: prev,mv=par[cur]; path.append(mv); cur=prev
    print(' state',sorted(s[0]),'carts',s[2],'len',len(path))
    for m in reversed(path): print('   ',m)
    break
