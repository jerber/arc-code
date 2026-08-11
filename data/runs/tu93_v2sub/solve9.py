import parse, game, full2
from collections import deque
OPP=full2.OPP

def search(W, init, T=60, optimistic_ambig=True, no_reverse=False):
    """BFS; ambiguity in the hunter's tie-break explored as separate branches (optimistic).
       no_reverse: hunter refuses to reverse -> then it stays put."""
    prev={init:None}; q=deque([init]); found=None
    while q and not found:
        st=q.popleft(); P,H,hdir,act,t,red=st
        if P==W.goal: found=st; break
        if t>T: continue
        F=W.forb(red)
        for d,nn in W.adj[P].items():
            if nn in F or nn==H: continue
            bad=False
            for tr in W.trs:
                op,_=tr[t]; np_,_=tr[t+1]
                if np_==nn: bad=True; break
            if bad: continue
            nact = act or (nn in W.gazeline(H,hdir))
            nred = red-{nn} if nn in red else red
            if not act:
                succ=[(hdir,H)]
            else:
                D=W.dist(nn); best=None; opts=[]
                for hd,hn in W.adj[H].items():
                    if hn not in D: continue
                    if best is None or D[hn]<best: best=D[hn]; opts=[(hd,hn)]
                    elif D[hn]==best: opts.append((hd,hn))
                stt=[o for o in opts if o[0]==hdir]
                if stt: opts=stt
                else:
                    nr=[o for o in opts if o[0]!=OPP.get(hdir)]
                    if nr: opts=nr
                    elif no_reverse: opts=[(hdir,H)]
                succ=opts if optimistic_ambig else opts[:1]
            for hd,h2 in succ:
                if h2==nn: continue
                ns=(nn,h2,hd,nact,t+1,nred)
                if ns not in prev: prev[ns]=(st,d); q.append(ns)
    if not found: return None
    acts=[];st=found
    while prev[st]: st,d=prev[st]; acts.append(d)
    return acts[::-1]
