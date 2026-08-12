import game,world,sys
def replay(E,path):
    carts=sorted(E['carts'].items())
    kinds=tuple(v[0] for k,v in carts)
    pos=tuple(k for k,v in carts); load=tuple(v[1]=='P' for k,v in carts)
    pegs=frozenset(k for k,v in E['cells'].items() if v=='P')
    print('start carts',list(zip(kinds,pos,load)),'pegs',sorted(pegs))
    for mv in path:
        if mv[0]!='JUMP':
            d=[k for k,v in game.DIRNAME.items() if v==mv[0]][0]
            pos=game.move_carts(pos,kinds,d,E['edges'])
            print(mv[0],'-> carts',pos)
        else:
            _,a,b,c=mv
            pg=set(pegs); ld=list(load)
            for q in (a,b):
                if q in E['pivots']: continue
                hit=False
                for i,pp in enumerate(pos):
                    if pp==q:
                        if kinds[i]=='V': hit=True
                        elif ld[i]: ld[i]=False; hit=True
                        break
                if not hit: pg.discard(q)
            placed=False
            for i,pp in enumerate(pos):
                if pp==c and kinds[i]=='S': ld[i]=True; placed=True; break
            if not placed: pg.add(c)
            pegs=frozenset(pg); load=tuple(ld)
            print('JUMP',a,b,c,'-> pegs',sorted(pegs),'load',load)
    print('final pegs',len(pegs)+sum(load))
if __name__=='__main__':
    E=game.extract(); r=game.solve(E)
    if r: replay(E,r)
