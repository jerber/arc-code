"""AND-OR search vs a BFS chaser that wakes when the player enters its gaze line (range<=2)."""
import game, patrol
from collections import deque
import sys
DELTA=game.DELTA
sys.setrecursionlimit(200000)

class H:
    def __init__(self, g, goal=None, chaser_colors='d'):
        L=patrol.Lv(g,goal=goal); self.L=L
        self.adj=L.adj; self.nodes=L.nodes; self.goal=L.goal; self.start=L.start
        self.chaser=None; self.statics={}
        for k,d in L.statics.items():
            v=L.B.val(*k)
            if v in chaser_colors: self.chaser=(k,d)
            else: self.statics[k]=d
        self._dist={}
    def dist(self,a):
        if a in self._dist: return self._dist[a]
        D={a:0}; q=deque([a])
        while q:
            c=q.popleft()
            for n in self.adj[c].values():
                if n not in D: D[n]=D[c]+1; q.append(n)
        self._dist[a]=D; return D
    def gazeline(self, mpos, mdir, rng=2):
        out=[]; cur=mpos
        for _ in range(rng):
            if mdir not in self.adj[cur]: break
            cur=self.adj[cur][mdir]; out.append(cur)
        return out

def solve(H_, maxdepth=40):
    goal=H_.goal
    mstart,mdir=H_.chaser
    def forb(red):
        f=set()
        for k in red:
            d=H_.statics[k]
            if d: dx,dy=DELTA[d]; f.add((k[0]+2*dx,k[1]+2*dy))
        return f
    memo={}
    def moves(M,P):
        D=H_.dist(P)
        cands=[n for n in H_.adj[M].values() if n in D]+[M]
        best=min(D[c] for c in cands)
        return [c for c in cands if D[c]==best]
    def win(P,M,act,red,depth):
        if P==goal: return []
        if depth==0: return None
        key=(P,M,act,red,depth)
        if key in memo: return memo[key]
        memo[key]=None
        F=forb(red); best=None
        for d,nn in H_.adj[P].items():
            if nn in F or nn==M: continue
            nred=red-{nn} if nn in red else red
            if nn==goal: best=[d]; break
            nact=act or (nn in H_.gazeline(M,mdir))
            if not act:
                # chaser does not move this tick (asleep, or first sighting = reaction delay)
                r=win(nn,M,nact,nred,depth-1)
                if r is not None:
                    c=[d]+r
                    if best is None or len(c)<len(best): best=c
            else:
                ok=True; sub=None
                for M2 in moves(M,nn):
                    if M2==nn: ok=False; break
                    r=win(nn,M2,True,nred,depth-1)
                    if r is None: ok=False; break
                    if sub is None or len(r)>len(sub): sub=r   # worst case length
                if ok:
                    c=[d]+(sub or [])
                    if best is None or len(c)<len(best): best=c
        memo[key]=best
        return best
    for dep in range(1,maxdepth+1):
        memo.clear()
        r=win(H_.start,mstart,False,frozenset(H_.statics),dep)
        if r is not None: return r
    return None
