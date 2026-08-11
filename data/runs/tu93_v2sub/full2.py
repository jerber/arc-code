"""Corrected hunter model: shortest-path step, prefers to continue straight, then turn, never reverses unless forced."""
import game, patrol
from collections import deque
DELTA=game.DELTA
OPP={'U':'D','D':'U','L':'R','R':'L'}

class World:
    def __init__(self, g, goal=None):
        L=patrol.Lv(g,goal=goal); self.L=L; self.adj=L.adj; self.goal=L.goal
        self.start=L.start
        self.pats=[]; self.hunter=None; self.reds={}
        for i,j,v,d in L.B.entities()['guards']:
            if v=='c': self.pats.append(((i,j),d))
            elif v=='d': self.hunter=((i,j),d)
            else: self.reds[(i,j)]=d
        self.trs=[patrol.traj(L,p,d,300) for p,d in self.pats]
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
    def hsteps(self,H,hdir,P):
        """returns list of (dir,node) candidates after preference filtering (len>1 => ambiguous)"""
        D=self.dist(P); best=None; opts=[]
        for d,n in self.adj[H].items():
            if n not in D: continue
            if best is None or D[n]<best: best=D[n]; opts=[(d,n)]
            elif D[n]==best: opts.append((d,n))
        if len(opts)<=1: return opts
        st=[o for o in opts if o[0]==hdir]
        if st: return st
        nr=[o for o in opts if o[0]!=OPP.get(hdir)]
        if nr: return nr
        return opts
    def forb(self,reds):
        f=set()
        for k in reds:
            d=self.reds[k]
            if d: dx,dy=DELTA[d]; f.add((k[0]+2*dx,k[1]+2*dy))
        return f

def search(W, targets, T=60, init=None, allow_ambiguous=False):
    """BFS to any state whose P,t matches a (pos, tmod, mod) target spec. Returns (acts, state)."""
    if init is None:
        init=(W.start, W.hunter[0], W.hunter[1], False, 0, frozenset(W.reds))
    prev={init:None}; q=deque([init]); found=None
    while q:
        st=q.popleft(); P,H,hdir,act,t,red=st
        for (pos,tmod,mod) in targets:
            if P==pos and (mod==0 or t%mod==tmod): found=st; break
        if found: break
        if t>T: continue
        F=W.forb(red)
        for d,nn in W.adj[P].items():
            if nn in F or nn==H: continue
            bad=False
            for tr in W.trs:
                op,_=tr[t]; np_,_=tr[t+1]
                if np_==nn: bad=True; break
            if bad: continue
            nact= act or (nn in W.gazeline(H,hdir))
            if act:
                opts=W.hsteps(H,hdir,nn)
                if not opts: opts=[(hdir,H)]
                if len(opts)>1 and not allow_ambiguous: continue
                ok=True
                for (hd,h2) in opts:
                    if h2==nn: ok=False; break
                if not ok: continue
                hd,h2=opts[0]
            else:
                hd,h2=hdir,H
            nred=red-{nn} if nn in red else red
            ns=(nn,h2,hd,nact,t+1,nred)
            if ns not in prev: prev[ns]=(st,d); q.append(ns)
    if not found: return None,None
    acts=[];st=found
    while prev[st]: st,d=prev[st]; acts.append(d)
    return acts[::-1], found

def trace(W, acts, init=None):
    if init is None: init=(W.start, W.hunter[0], W.hunter[1], False, 0, frozenset(W.reds))
    P,H,hdir,act,t,red=init; out=[]
    for d in acts:
        nn=W.adj[P].get(d)
        if nn is None: out.append(('ILLEGAL',d,P)); break
        pats=tuple(tr[t+1][0] for tr in W.trs)
        note=[]
        if nn in pats: note.append('PATROLLER')
        if nn in W.forb(red): note.append('REDGAZE')
        nact=act or nn in W.gazeline(H,hdir)
        if act:
            opts=W.hsteps(H,hdir,nn)
            if len(opts)>1: note.append('AMBIG'+str(opts))
            hdir,H=opts[0]
            if H==nn: note.append('HUNTER')
        act=nact
        if nn in red: red=red-{nn}
        P=nn; t+=1
        out.append((t,d,P,H,hdir,pats,','.join(note)))
    return out
