#!/usr/bin/env python3
"""Drive the active L8 rectangle; identifies its colour/state from the board each round."""
import subprocess, collections, parse, plan8, rect3

BUD=26
def read_state():
    bl=parse.load(); g=bl[-1][1][-1][1]
    m=[(x,y) for y in range(63) for x in range(64) if g[y][x]=='0']
    if not m: return None,g
    mx,my=m[0]
    best=None
    for c in set("".join(g[:63]))-set('5402'):
        S={(x,y) for y in range(63) for x in range(64) if g[y][x]==c}
        rows=collections.Counter(y for x,y in S)
        cand=sorted(y for y,n in rows.items() if n>=3)
        for T in cand:
            for B in cand:
                if B<T: continue
                h=B-T+1; w=BUD-h
                if not (1<=w<=25): continue
                L=mx-((w)//2)
                # predicted cells
                R=L+w-1
                cells=set()
                for x in range(L,R+1): cells.add((x,T)); cells.add((x,B))
                for y in range(T,B+1): cells.add((L,y)); cells.add((R,y))
                onb=[p for p in cells if 0<=p[0]<64 and 0<=p[1]<63]
                if not onb: continue
                good=sum(1 for p in onb if g[p[1]][p[0]]==c)/len(onb)
                cy=(T+B)/2
                if abs(-(-((2*T+h-1))//2)-my)>0: continue
                sc=(good,len(onb))
                if good>=0.9 and (best is None or sc>best[0]): best=(sc,(L,T,w,c))
    return (best[1] if best else None), g

def act(moves,plan):
    r=subprocess.run(["./act","do","--plan",plan]+moves,capture_output=True,text=True)
    return r.stdout.strip().split("\n")[-2:]

def drive(goal,maxrounds=60,label="drive"):
    G=plan8.setup(); banned=set(); last=None
    for rnd in range(maxrounds):
        st,g=read_state()
        if st is None: print("cannot read state"); return False
        L,T,w,col=st
        print(f"round {rnd}: L={L} R={L+w-1} T={T} B={T+BUD-w-1} w={w} col={col}")
        if goal((L,T,w,col)): print("GOAL"); return True
        if last is not None and last[0]==(L,T,w,col):
            banned.add((L,T,w,last[1]))
            print("   STUCK: banning",last[1],"at",(L,T,w))
        plans={}
        for vg in (0,1):
            for hg in (0,1):
                p,cut,tr=plan8.plan((L,T,w,col,vg,hg), lambda x: goal(x[:4]), G, banned)
                if p: plans[(vg,hg)]=(p,cut)
        if not plans: print("NO PLAN from",st); return False
        pl=[v[0] for v in plans.values()]; n=min(v[1] for v in plans.values())
        common=0
        while common<n and len(set(p[common] for p in pl))==1: common+=1
        if common==0: common=1
        moves=pl[0][:common]
        print(f"   {len(moves)} moves (plan len {len(pl[0])}):", " ".join(moves[:14]))
        last=((L,T,w,col),moves[0])
        out=act(moves,f"{label} leg {rnd}")
        print("   ", out[-2] if len(out)>1 else out)
        if "score=8" in " ".join(out): print("LEVEL CLEARED"); return True
    return False
