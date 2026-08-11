"""Search for a safe route past straight-line patrollers (1 node per player action, bounce at ends)."""
from collections import deque
import game

DELTA=game.DELTA
OPP={'U':'D','D':'U','L':'R','R':'L'}

class Lv:
    def __init__(self, g, goal=None):
        B=game.Board(g); self.B=B; self.gr=B.grid(); E=B.entities(); self.E=E
        self.goal=goal or E['goal']; self.start=(E['player'][0],E['player'][1])
        px,py=self.start
        self.nodes=set()
        for j in range(B.H):
            for i in range(B.W):
                if (i-px)%2==0 and (j-py)%2==0 and self.gr[j][i]!='5':
                    self.nodes.add((i,j))
        self.adj={n:{} for n in self.nodes}
        for n in self.nodes:
            i,j=n
            for d,(dx,dy) in DELTA.items():
                mid=(i+dx,j+dy); nn=(i+2*dx,j+2*dy)
                if nn in self.nodes and self.gr[mid[1]][mid[0]]!='5':
                    self.adj[n][d]=nn
        self.patrols=[]; self.statics={}
        for i,j,v,d in E['guards']:
            if v=='c': self.patrols.append([(i,j),d])
            else: self.statics[(i,j)]=d

def traj(L, pos, d, T):
    """positions of a bouncing patroller for ticks 1..T (index 0 = current), with facing"""
    out=[(pos,d)]
    for _ in range(T):
        if d in L.adj[pos]:
            pos=L.adj[pos][d]
        else:
            d=OPP[d]
            pos=L.adj[pos].get(d,pos)
        out.append((pos,d))
    return out

def search(L, T=40, allow_kill_patrol=True, follow_forbidden=False):
    trs=[traj(L,p,d,T+1) for p,d in L.patrols]
    red0=frozenset(L.statics)
    def forb(red):
        f=set()
        for k in red:
            d=L.statics[k]
            if d: dx,dy=DELTA[d]; f.add((k[0]+2*dx,k[1]+2*dy))
        return f
    start=(L.start,0,red0,tuple(range(len(L.patrols))))
    prev={start:None}; q=deque([start]); goalst=None
    while q:
        st=q.popleft(); P,t,red,alive=st
        if P==L.goal: goalst=st; break
        if t>=T: continue
        F=forb(red)
        for d,nn in L.adj[P].items():
            # patroller states at tick t (before move) and t+1 (after their move)
            killed=[]
            bad=False
            for idx in alive:
                op,od=trs[idx][t]
                np_,nd=trs[idx][t+1]
                if np_==nn: bad=True; break        # it moves onto our destination
                if np_==P and op==nn: bad=True; break  # swap
                if op==nn and follow_forbidden: bad=True; break
            if bad: continue
            if nn in F: continue
            nred=red-{nn} if nn in red else red
            nalive=tuple(i for i in alive if i not in killed)
            ns=(nn,t+1,nred,nalive)
            if ns not in prev: prev[ns]=(st,d); q.append(ns)
    if goalst is None: return None
    acts=[]; st=goalst
    while prev[st]: st,d=prev[st]; acts.append(d)
    return acts[::-1]
