import re
from collections import deque,Counter

def grid(path):
    L=[l.strip() for l in open(path)]
    return [l for l in L if re.fullmatch(r'[0-9a-f]{64}',l)]

def comps(g,chars):
    seen=[[0]*64 for _ in range(64)]; out=[]
    for y in range(64):
        for x in range(64):
            if g[y][x] in chars and not seen[y][x]:
                q=deque([(x,y)]); seen[y][x]=1; cs=[]
                while q:
                    cx,cy=q.popleft(); cs.append((cx,cy))
                    for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
                        nx,ny=cx+dx,cy+dy
                        if 0<=nx<64 and 0<=ny<64 and g[ny][nx] in chars and not seen[ny][nx]:
                            seen[ny][nx]=1; q.append((nx,ny))
                out.append(cs)
    return out

class Board:
    def __init__(self,g):
        self.g=g
        tiles=[c for c in comps(g,set('1e23')) if len(c)>=8]
        ox=Counter(min(p[0] for p in c)%6 for c in tiles).most_common(1)[0][0]
        oy=Counter(min(p[1] for p in c)%6 for c in tiles).most_common(1)[0][0]
        self.ox,self.oy=ox,oy
        self.cells={}   # (X,Y) -> 'PEG'|'HOLE'|'SPEG'|'SHUTTLE'
        self.track=set()
        self.NX=(64-ox)//6+1; self.NY=(64-oy)//6+1
        for Y in range(self.NY):
            for X in range(self.NX):
                x0,y0=ox+6*X,oy+6*Y
                if x0<0 or y0<0 or x0+3>63 or y0+3>63: continue
                c=Counter(g[y0+dy][x0+dx] for dy in range(4) for dx in range(4))
                s=set(c)
                if 'c' in s: self.cells[(X,Y)]='SPEG' if 'e' in s else 'SHUTTLE'
                elif 'e' in s: self.cells[(X,Y)]='PEG'
                elif s<=set('12'): self.cells[(X,Y)]='HOLE'
                # track band
                ctr=all(g[y0+r][x0+c]=='5' for r in (1,2) for c in (1,2))
                if ctr and (X,Y) not in self.cells: self.track.add((X,Y))
        # shuttles also occupy track
        for k,v in self.cells.items():
            if v.startswith('S') or v=='SHUTTLE': self.track.add(k)
        self.edges=set()   # undirected pairs
        for (X,Y) in list(self.cells)+list(self.track):
            for dx,dy in((1,0),(0,1)):
                n=(X+dx,Y+dy)
                if n not in self.cells and n not in self.track: continue
                x0,y0=ox+6*X,oy+6*Y
                if dx: gp=[g[y0+r][x0+4+k] for r in (1,2) for k in (0,1)]
                else:  gp=[g[y0+4+k][x0+c] for c in (1,2) for k in (0,1)]
                if set(gp)<=set('0'): self.edges.add((((X,Y)),n,'panel'))
                elif set(gp)<=set('5bc'): self.edges.add((((X,Y)),n,'track'))
                elif set(gp)<=set('05bc9') and '5' in set(gp): self.edges.add((((X,Y)),n,'dock'))
    def dump(self):
        print('offset',self.ox,self.oy)
        print('cells:')
        for k in sorted(self.cells,key=lambda t:(t[1],t[0])): print('  ',k,self.cells[k])
        print('track:',sorted(self.track,key=lambda t:(t[1],t[0])))
        print('edges:')
        for e in sorted(self.edges,key=lambda e:(e[0][1],e[0][0])): print('  ',e)
if __name__=='__main__':
    import sys
    Board(grid(sys.argv[1])).dump()
