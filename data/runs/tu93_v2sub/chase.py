"""Guaranteed-win search against chasers that move 1 node per player move."""
from collections import deque
import game

DELTA=game.DELTA

class Level:
    def __init__(self, g, chaser_colors='c', static_colors='8'):
        B=game.Board(g); self.B=B
        gr=B.grid(); self.gr=gr
        E=B.entities(); self.E=E
        self.goal=E['goal']
        self.start=(E['player'][0],E['player'][1])
        self.chasers=[]; self.statics={}
        for i,j,v,d in E['guards']:
            if v in chaser_colors: self.chasers.append(((i,j),d,v))
            elif v in static_colors: self.statics[(i,j)]=d
        # node set: parity of start
        px,py=self.start
        self.nodes=set()
        for j in range(B.H):
            for i in range(B.W):
                if (i-px)%2==0 and (j-py)%2==0 and gr[j][i]!='5':
                    self.nodes.add((i,j))
        self.adj={n:{} for n in self.nodes}
        for (i,j) in self.nodes:
            for d,(dx,dy) in DELTA.items():
                mid=(i+dx,j+dy); nn=(i+2*dx,j+2*dy)
                if nn in self.nodes and 0<=mid[0]<B.W and 0<=mid[1]<B.H and gr[mid[1]][mid[0]]!='5':
                    self.adj[(i,j)][d]=nn
    def dist(self, a):
        D={a:0}; q=deque([a])
        while q:
            c=q.popleft()
            for d,n in self.adj[c].items():
                if n not in D: D[n]=D[c]+1; q.append(n)
        return D
    def forbidden(self, redalive):
        f=set()
        for k in redalive:
            d=self.statics[k]
            if d:
                dx,dy=DELTA[d]; f.add((k[0]+2*dx,k[1]+2*dy))
        return f

def chaser_moves(L, O, P):
    """set of nodes the chaser may move to: neighbours minimising distance to P (stays if none better/equal)"""
    D=L.dist(P)
    best=None; res=[]
    cands=[O]+list(L.adj[O].values())
    for n in cands:
        if n not in D: continue
        if best is None or D[n]<best: best=D[n]; res=[n]
        elif D[n]==best: res.append(n)
    return set(res) if res else {O}

def search(L, maxdepth=45, kill_chaser=False):
    """AND-OR search: returns dict state->best move for guaranteed win, or None."""
    O0=tuple(c[0] for c in L.chasers)
    red0=frozenset(L.statics)
    goal=L.goal
    memo={}
    import sys
    sys.setrecursionlimit(100000)
    def win(P,O,red,depth,path):
        if P==goal: return []
        if depth==0: return None
        key=(P,O,red,depth)
        if key in memo: return memo[key]
        memo[key]=None  # cycle guard
        forb=L.forbidden(red)
        best=None
        for d,nn in sorted(L.adj[P].items()):
            if nn in forb: continue
            if nn in O and not kill_chaser: continue
            nred=red-{nn} if nn in red else red
            if nn==goal: best=[d]; break
            # chaser responses (adversarial over ties)
            newO=[nn2 for nn2 in O]
            optsets=[]
            for idx,op in enumerate(O):
                if kill_chaser and nn==op:
                    optsets.append([None]); continue
                optsets.append(sorted(chaser_moves(L,op,nn)))
            ok=True; sub=None
            import itertools
            for combo in itertools.product(*optsets):
                combo=tuple(c for c in combo)
                if any(c==nn for c in combo if c is not None): ok=False; break
                cO=tuple(c for c in combo if c is not None)
                r=win(nn,cO,nred,depth-1,path+[d])
                if r is None: ok=False; break
                if sub is None or len(r)<len(sub): sub=r
            if ok:
                cand=[d]+(sub or [])
                if best is None or len(cand)<len(best): best=cand
        memo[key]=best
        return best
    for dep in range(1,maxdepth+1):
        memo.clear()
        r=win(L.start,O0,red0,dep,[])
        if r is not None: return r
    return None
