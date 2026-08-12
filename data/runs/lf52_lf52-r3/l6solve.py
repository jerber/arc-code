import l6,game,heapq,sys
E=l6.E
def search(goalfn,maxexp=800000,hfn=None):
    cells=E['cells']; pivots=E['pivots']; edges=E['edges']; reds0=frozenset(E['reds'])
    carts=sorted(E['carts'].items()); kinds=tuple(v[0] for k,v in carts)
    pos0=tuple(k for k,v in carts); load0=tuple(v[1]=='P' for k,v in carts)
    pegs0=frozenset(k for k,v in cells.items() if v=='P'); holes=set(cells)
    start=(pegs0,reds0,pos0,load0)
    def succ(st):
        pegs,reds,pos,load=st; out=[]
        for d in game.DIRS:
            np_=game.move_carts(pos,kinds,d,edges)
            if np_!=pos: out.append(((pegs,reds,np_,load),(game.DIRNAME[d],)))
        occ=set(pegs)|set(pivots)|set(reds); land=set(holes)-set(reds)
        for i,p_ in enumerate(pos):
            if kinds[i]=='V': occ.add(p_)
            else:
                land.add(p_)
                if load[i]: occ.add(p_)
        movers=[(a,'peg') for a in pegs]+[(a,'red') for a in reds]+[(p_,'s%d'%i) for i,p_ in enumerate(pos) if kinds[i]=='S' and load[i]]
        for a,typ in movers:
            for d in game.DIRS:
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
    h=hfn or (lambda st:0)
    pq=[(h(start),0,0,start,[])]; best={start:0}; cnt=0; exp=0
    while pq:
        f,g,_,st,path=heapq.heappop(pq)
        if goalfn(st): return path,st
        if g>best.get(st,1e9): continue
        exp+=1
        if exp>maxexp: return None,None
        for nst,mv in succ(st):
            ng=g+(2 if mv[0]=='JUMP' else 1)
            if ng<best.get(nst,1e9):
                best[nst]=ng; cnt+=1
                heapq.heappush(pq,(ng+h(nst),ng,cnt,nst,path+[mv]))
    return None,None
