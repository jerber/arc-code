import parse
from collections import deque

def blockgrid(g, N=11, x0=15, y0=15, s=3):
    return [[g[y0+s*j][x0+s*i] for i in range(N)] for j in range(N)]

def bfs(bg, start, goal, walls='5'):
    N=len(bg); M=len(bg[0])
    q=deque([start]); prev={start:None}
    while q:
        c=q.popleft()
        if c==goal: break
        x,y=c
        for dx,dy,name in ((0,-1,'U'),(0,1,'D'),(-1,0,'L'),(1,0,'R')):
            n=(x+dx,y+dy)
            if 0<=n[0]<M and 0<=n[1]<N and bg[n[1]][n[0]] not in walls and n not in prev:
                prev[n]=c; q.append(n)
    if goal not in prev: return None
    path=[]; c=goal
    while c: path.append(c); c=prev[c]
    return path[::-1]

def dirs(path):
    out=[]
    for a,b in zip(path,path[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        out.append({(0,-1):'U',(0,1):'D',(-1,0):'L',(1,0):'R'}[(dx,dy)])
    return out
