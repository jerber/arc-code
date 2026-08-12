"""BFS over corridor pieces + 2 west shuttles + camera."""
from collections import deque
import sys
CORR=[(c,3) for c in range(15,26)]
TRACK=[(c,7) for c in range(8,19)]+[(15,5),(15,6),(18,5),(18,6)]
TI={p:i for i,p in enumerate(TRACK)}
PIV={(15,3):(15,4),(18,3):(18,4)}   # corridor cell -> pivot -> dock track cell
DOCK={(15,3):(15,5),(18,3):(18,5)}
DIRS={'1':(0,-1),'2':(0,1),'3':(-1,0),'4':(1,0)}
CAMMAX=104
# piece location encoding: 0..10 corridor idx, 11=inX, 12=inY, 13=dead
def vis(cell,cam):
    x0=6*cell[0]-cam
    return x0<=63 and x0+3>=0
def press(pos,cargo,act):
    d=DIRS[act]; p=list(pos); moved={}
    for _ in range(3):
        for i in (0,1):
            if i in moved: continue
            t=(p[i][0]+d[0],p[i][1]+d[1])
            if t in TI and t not in p:
                p[i]=t; moved[i]=d[0]
    if not moved: return None,0
    dx=0
    for i,dd in moved.items():
        if cargo[i]=='G': dx=dd*6
    return tuple(p),dx
def succ(st):
    A,B,R,X,Y,cam=st
    pos=(TRACK[X],TRACK[Y])
    cargo=[None,None]
    for who,loc in (('A',A),('B',B),('R',R)):
        v='G' if who in 'AB' else 'R'
        if loc==11: cargo[0]=v
        if loc==12: cargo[1]=v
    out=[]
    for act in '1234':
        np,dx=press(pos,cargo,act)
        if np is None: continue
        nc=max(0,min(CAMMAX,cam+dx))
        out.append(((A,B,R,TI[np[0]],TI[np[1]],nc),'P'+act))
    # jumps
    occ={}
    for who,loc in (('A',A),('B',B),('R',R)):
        if loc<11: occ[CORR[loc]]=who
    val={'A':'G','B':'G','R':'R'}
    locs={'A':A,'B':B,'R':R}
    for who in 'ABR':
        loc=locs[who]
        if loc==13: continue
        if loc<11:
            a=CORR[loc]
            # horizontal jumps
            for dxs in (1,-1):
                b=(a[0]+dxs,3); c=(a[0]+2*dxs,3)
                if b not in occ or c not in CORR or c in occ: continue
                if not(vis(a,cam) and vis(c,cam)): continue
                nl=dict(locs); nl[who]=CORR.index(c)
                if val[who]=='G' and val[occ[b]]=='G': nl[occ[b]]=13
                out.append(((nl['A'],nl['B'],nl['R'],X,Y,cam),'J%s%s>%s'%(who,a,c)))
            # load into shuttle over pivot
            if a in DOCK:
                d=DOCK[a]
                for i,sp in enumerate(pos):
                    if sp==d and cargo[i] is None:
                        if not(vis(a,cam) and vis(d,cam)): continue
                        nl=dict(locs); nl[who]=11+i
                        out.append(((nl['A'],nl['B'],nl['R'],X,Y,cam),'L%s%s'%(who,a)))
        else:
            i=loc-11; sp=pos[i]
            for cell,d in DOCK.items():
                if sp==d and cell not in occ:
                    if not(vis(cell,cam) and vis(d,cam)): continue
                    nl=dict(locs); nl[who]=CORR.index(cell)
                    out.append(((nl['A'],nl['B'],nl['R'],X,Y,cam),'U%s%s'%(who,cell)))
    return out
def goal(st):
    A,B,R,X,Y,cam=st
    if cam!=104: return False
    if R<11: return False           # red must be in a shuttle
    g=[A,B]
    incorr=[x for x in g if x<11]; insh=[x for x in g if x in (11,12)]
    if len(incorr)!=1 or len(insh)!=1: return False
    c=CORR[incorr[0]][0]
    return c%2==1 and c>=17
def bfs(start,maxstates=4000000):
    seen={start:None}; q=deque([start]); n=0
    while q:
        st=q.popleft(); n+=1
        if n%400000==0: print('  visited',n,'queue',len(q),file=sys.stderr)
        for ns,mv in succ(st):
            if ns in seen: continue
            seen[ns]=(st,mv)
            if goal(ns):
                path=[]; cur=ns
                while seen[cur]: p,m=seen[cur]; path.append(m); cur=p
                return list(reversed(path)),len(seen)
            q.append(ns)
            if len(seen)>maxstates: return None,len(seen)
    return None,len(seen)
if __name__=='__main__':
    start=(0,1,3,TI[(15,5)],TI[(18,5)],62)   # A(15,3) B(16,3) R(18,3)
    p,ns=bfs(start)
    print('states',ns)
    print('plan',p)

def explore(start,maxstates=4000000):
    seen={start:None}; q=deque([start])
    while q:
        st=q.popleft()
        for ns,mv in succ(st):
            if ns in seen: continue
            seen[ns]=(st,mv); q.append(ns)
    return seen
