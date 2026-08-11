import game,sys
from collections import deque
def route(E,goal,maxd=40):
    carts=sorted(E['carts'].items())
    kinds=tuple(v[0] for k,v in carts); pos=tuple(k for k,v in carts)
    names=[v[0] for k,v in carts]
    seen={pos:[]}; q=deque([pos])
    while q:
        p=q.popleft()
        if goal(dict(zip(names,p)) if len(set(names))==len(names) else p,p): return seen[p],names,p
        if len(seen[p])>=maxd: continue
        for d in game.DIRS:
            n=game.move_carts(p,kinds,d,E['edges'])
            if n not in seen:
                seen[n]=seen[p]+[game.DIRNAME[d]]; q.append(n)
    return None,names,None
if __name__=='__main__':
    E=game.extract()
    carts=sorted(E['carts'].items()); print('order',carts)
    expr=sys.argv[1]
    g=eval('lambda m,p: '+expr)
    r,names,fin=route(E,g)
    print(names,r,'->',fin)
