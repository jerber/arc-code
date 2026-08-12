#!/usr/bin/env python3
"""Drive an L8 rectangle to its goal: observe board -> plan -> execute a safe prefix."""
import subprocess, sys, collections, parse, sim, rect3, plan8

SW_CELLS=None
def read_state(colour, exclude):
    bl=parse.load(); g=bl[-1][1][-1][1]
    m=[(x,y) for y in range(63) for x in range(64) if g[y][x]=='0']
    S={(x,y) for y in range(63) for x in range(64) if g[y][x]==colour} - exclude
    rows=collections.Counter(y for x,y in S)
    cand=[y for y,n in rows.items() if n>=3]
    if not m or len(cand)<1: return None,g
    mx,my=m[0]
    T=min(cand); B=max(cand)
    h=B-T+1; w=26-h
    L=mx-((w-1+1)//2)
    return (L,T,w,colour),g

def act(moves,plan):
    cmd=["./act","do","--plan",plan]+moves
    r=subprocess.run(cmd,capture_output=True,text=True)
    return r.stdout.strip().split("\n")[-2:]

def drive(colour, exclude, goal, maxrounds=40):
    G=plan8.setup()
    for rnd in range(maxrounds):
        st,g=read_state(colour,exclude)
        if st is None: print("cannot read state"); return False
        L,T,w,col=st
        print(f"round {rnd}: L={L} T={T} w={w} h={26-w} col={col}")
        if goal((L,T,w,col)): print("GOAL reached"); return True
        plans={}
        for vg in (0,1):
            for hg in (0,1):
                p,cut,tr=plan8.plan((L,T,w,col,vg,hg), lambda x: goal(x[:4]), G)
                if p: plans[(vg,hg)]=(p,cut)
        if not plans: print("NO PLAN"); return False
        # longest common prefix, capped at first squeeze of the shortest plan
        pl=[v[0] for v in plans.values()]; cuts=[v[1] for v in plans.values()]
        n=min(cuts)
        common=0
        while common<n and len(set(p[common] for p in pl))==1: common+=1
        if common==0: common=1
        moves=pl[0][:common]
        print("   executing",len(moves),"moves:"," ".join(moves[:12]),"..." if len(moves)>12 else "")
        out=act(moves,f"L8 drive {colour}: leg {rnd}")
        print("   ",out[-2] if len(out)>1 else out)
        if "score" in " ".join(out) and "score=8" in " ".join(out): return True
    return False
