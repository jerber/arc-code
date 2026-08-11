import sys, subprocess, json, re
from board import grid, comps
WALLS={(15,2),(17,2),(13,4),(19,4),(21,4)}
def view():
    subprocess.run('./act board>/tmp/cur.txt',shell=True,check=True)
    g=grid('/tmp/cur.txt')
    tiles=[c for c in comps(g,set('1e23')) if len(c)>=12]
    from collections import Counter
    ox=Counter(min(p[0] for p in c)%6 for c in tiles).most_common(1)[0][0]
    oy=Counter(min(p[1] for p in c)%6 for c in tiles).most_common(1)[0][0]
    ws=[]
    for c in comps(g,set('f7')):
        if len(c)>6:
            x0=min(p[0] for p in c); y0=min(p[1] for p in c)+1
            ws.append(((x0-ox)//6,(y0-oy)//6))
    best=None
    for dx in range(-30,31):
        for dy in range(-20,21):
            m=sum(1 for (X,Y) in ws if (X+dx,Y+dy) in WALLS)
            if best is None or m>best[0]: best=(m,dx,dy)
    return g,ox,oy,best[1],best[2]
def pix(ox,oy,dx,dy,w):
    return (ox+6*(w[0]-dx)+1, oy+6*(w[1]-dy)+1)
JUMPS=json.load(open('/tmp/jumps.json'))
i=int(sys.argv[1]); n=int(sys.argv[2])
g,ox,oy,dx,dy=view()
acts=[]
for (a,c) in JUMPS[i:i+n]:
    for w in (a,c):
        x,y=pix(ox,oy,dx,dy,tuple(w)); acts.append(f'ACTION6:{x},{y}')
print('offset',dx,dy)
print(' '.join(acts))
