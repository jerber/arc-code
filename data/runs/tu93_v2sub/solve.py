import parse, subprocess
from collections import deque

DIRACT={'U':'ACTION1','D':'ACTION2','L':'ACTION3','R':'ACTION4'}
DELTA={'U':(0,-1),'D':(0,1),'L':(-1,0),'R':(1,0)}
WALL='5'

def state(path='logs.txt'):
    return parse.lastgrid(path)

def bg(g, N=21):
    """block grid: centers of 3x3 blocks, plus set of all values in block"""
    return [[g[3*j+1][3*i+1] for i in range(N)] for j in range(N)]

def blockfull(g,N=21):
    out=[]
    for j in range(N):
        row=[]
        for i in range(N):
            s=set(g[3*j+dy][3*i+dx] for dy in range(3) for dx in range(3))
            row.append(s)
        out.append(row)
    return out

def locate(g, ch, N=21):
    B=blockfull(g,N)
    return [(i,j) for j in range(N) for i in range(N) if ch in B[j][i]]

def path(g, player='9', goal='e', blocked=WALL, N=21):
    b=bg(g,N)
    B=blockfull(g,N)
    P=[(i,j) for j in range(N) for i in range(N) if player in B[j][i]]
    G=[(i,j) for j in range(N) for i in range(N) if goal in B[j][i]]
    if not P or not G: return None,None,None
    start,gl=P[0],G[0]
    def ok(i,j):
        return 0<=i<N and 0<=j<N and b[j][i] not in blocked
    prev={start:None}; q=deque([start])
    while q:
        c=q.popleft()
        if c==gl: break
        for name,(dx,dy) in DELTA.items():
            mid=(c[0]+dx,c[1]+dy); n=(c[0]+2*dx,c[1]+2*dy)
            if ok(*mid) and ok(*n) and n not in prev:
                prev[n]=(c,name); q.append(n)
    if gl not in prev: return None,start,gl
    acts=[];c=gl
    while prev[c]: c,name=prev[c]; acts.append(name)
    return acts[::-1],start,gl

def actstr(dirs):
    return ' '.join(DIRACT[d] for d in dirs)
