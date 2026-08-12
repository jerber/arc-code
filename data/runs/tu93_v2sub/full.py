"""Full model: patrollers (deterministic), one hunter (BFS chaser, tie-break order), static reds."""
import game, patrol
from collections import deque
DELTA=game.DELTA
OPP={'U':'D','D':'U','L':'R','R':'L'}

class World:
    def __init__(self, g, goal=None, order='DLUR'):
        L=patrol.Lv(g,goal=goal); self.L=L; self.adj=L.adj; self.goal=L.goal
        self.start=L.start; self.order=order
        self.pats=[]; self.hunter=None; self.reds={}
        for i,j,v,d in L.B.entities()['guards']:
            if v=='c': self.pats.append(((i,j),d))
            elif v=='d': self.hunter=((i,j),d)
            else: self.reds[(i,j)]=d
        self.trs=[patrol.traj(L,p,d,200) for p,d in self.pats]
        self._D={}
    def dist(self,a):
        if a in self._D: return self._D[a]
        Dm={a:0}; q=deque([a])
        while q:
            c=q.popleft()
            for n in self.adj[c].values():
                if n not in Dm: Dm[n]=Dm[c]+1; q.append(n)
        self._D[a]=Dm; return Dm
    def gazeline(self,pos,d,rng=2):
        out=[];cur=pos
        for _ in range(rng):
            if d not in self.adj[cur]: break
            cur=self.adj[cur][d]; out.append(cur)
        return out
    def hunter_step(self,H,P):
        D=self.dist(P)
        best=None;opts=[]
        for d in 'UDLR':
            n=self.adj[H].get(d)
            if n is None or n not in D: continue
            if best is None or D[n]<best: best=D[n]; opts=[(d,n)]
            elif D[n]==best: opts.append((d,n))
        if not opts: return H,None
        for d in self.order:
            for (dd,n) in opts:
                if dd==d: return n,dd
        return opts[0][1],opts[0][0]
    def forb(self,reds):
        f=set()
        for k in reds:
            d=self.reds[k]
            if d: dx,dy=DELTA[d]; f.add((k[0]+2*dx,k[1]+2*dy))
        return f

def plan(W, T=70, hstart=None, hactive=False, start=None, t0=0, reds=None):
    H0=hstart or W.hunter[0]; hdir=W.hunter[1]
    P0=start or W.start
    r0=frozenset(W.reds if reds is None else reds)
    st0=(P0,H0,hactive,t0,r0)
    prev={st0:None}; q=deque([st0]); goalst=None
    while q:
        st=q.popleft(); P,H,act,t,red=st
        if P==W.goal: goalst=st; break
        if t-t0>T: continue
        F=W.forb(red)
        for d,nn in W.adj[P].items():
            if nn in F or nn==H: continue
            bad=False
            for tr in W.trs:
                op,_=tr[t]; np_,_=tr[t+1]
                if np_==nn or op==nn: bad=True; break
                if np_==P and op==nn: bad=True; break
            if bad: continue
            nact=act or (nn in W.gazeline(H,hdir) if not act else True)
            if act:
                H2,_=W.hunter_step(H,nn)
                if H2==nn: continue
            else:
                H2=H
            nred=red-{nn} if nn in red else red
            ns=(nn,H2,nact,t+1,nred)
            if ns not in prev: prev[ns]=(st,d); q.append(ns)
    if goalst is None: return None
    acts=[];st=goalst
    while prev[st]: st,d=prev[st]; acts.append(d)
    return acts[::-1]

def simulate(W, acts, hstart=None, hactive=False, start=None, t0=0, reds=None):
    P=start or W.start; H=hstart or W.hunter[0]; hdir=W.hunter[1]
    act=hactive; red=set(W.reds if reds is None else reds); t=t0
    out=[]
    for d in acts:
        nn=W.adj[P].get(d)
        if nn is None: out.append((d,'ILLEGAL',P,H)); break
        pats=[tr[t+1][0] for tr in W.trs]
        died=None
        if nn in pats: died='patroller'
        if nn in W.forb(red): died='red-gaze'
        newact = act or nn in W.gazeline(H,hdir)
        if act:
            H,_=W.hunter_step(H,nn)
            if H==nn: died='hunter'
        act=newact
        if nn in red: red.discard(nn)
        P=nn; t+=1
        out.append((t,d,P,H,act,tuple(pats),died))
        if died: break
    return out
