import parse
from collections import deque
DIRACT={'U':'ACTION1','D':'ACTION2','L':'ACTION3','R':'ACTION4'}
DELTA={'U':(0,-1),'D':(0,1),'L':(-1,0),'R':(1,0)}
REL={(0,1):'U',(2,1):'D',(1,0):'L',(1,2):'R'}  # (row,col)->dir

def load(path='logs.txt'):
    return parse.lastgrid(path)

def offsets(g, marker='9'):
    pts=[(x,y) for y in range(len(g)) for x in range(len(g[0])) if g[y][x]==marker]
    if not pts: return 0,0
    return min(p[0] for p in pts)%3, min(p[1] for p in pts)%3

class Board:
    def __init__(self, g):
        self.g=g
        self.ox,self.oy=offsets(g)
        self.W=(64-self.ox)//3
        self.H=(63-self.oy)//3   # row 63 is the HUD bar
    def px(self,i,j): return 3*i+self.ox, 3*j+self.oy
    def block(self,i,j):
        x,y=self.px(i,j)
        return [''.join(self.g[y+dy][x+dx] for dx in range(3)) for dy in range(3)]
    def val(self,i,j):
        """majority/body colour of block"""
        b=self.block(i,j)
        from collections import Counter
        return Counter(''.join(b)).most_common(1)[0][0]
    def facing(self,i,j):
        b=self.block(i,j); body=self.val(i,j)
        for (r,c),d in REL.items():
            if b[r][c]!=body: return d
        return None
    def grid(self):
        return [[self.val(i,j) for i in range(self.W)] for j in range(self.H)]
    def entities(self):
        out={'player':None,'goal':None,'guards':[],'other':[]}
        for j in range(self.H):
            for i in range(self.W):
                v=self.val(i,j)
                if v=='9': out['player']=(i,j,self.facing(i,j))
                elif v=='e': out['goal']=(i,j)
                elif v in '025': pass
                else: out['guards'].append((i,j,v,self.facing(i,j)))
        return out
    def dump(self):
        gr=self.grid()
        print(f'off=({self.ox},{self.oy}) size {self.W}x{self.H}')
        print('    '+''.join(f'{i%10}' for i in range(self.W)))
        for j in range(self.H): print(f'{j:3d} '+''.join(gr[j]))

def solve(g, killable='8c', blockers='5', extra_forbidden=()):
    B=Board(g); gr=B.grid(); E=B.entities()
    if not E['player'] or not E['goal']: return None,B,E
    px,py,_=E['player']; gx,gy=E['goal']
    guards={(i,j):(v,d) for i,j,v,d in E['guards']}
    def walk(i,j):
        return 0<=i<B.W and 0<=j<B.H and gr[j][i] not in blockers
    live=frozenset(k for k,(v,d) in guards.items() if v in killable)
    start=((px,py),live)
    prev={start:None}; q=deque([start]); goalst=None
    while q:
        st=q.popleft(); (cx,cy),alive=st
        if (cx,cy)==(gx,gy): goalst=st; break
        forb=set(extra_forbidden)
        for k in alive:
            v,d=guards[k]
            if d: dx,dy=DELTA[d]; forb.add((k[0]+2*dx,k[1]+2*dy))
        for name,(dx,dy) in DELTA.items():
            mid=(cx+dx,cy+dy); nn=(cx+2*dx,cy+2*dy)
            if not walk(*mid) or not walk(*nn): continue
            if nn in forb: continue
            ns=(nn, alive-{nn} if nn in alive else alive)
            if ns not in prev: prev[ns]=(st,name); q.append(ns)
    if goalst is None: return None,B,E
    acts=[]; st=goalst
    while prev[st]: st,name=prev[st]; acts.append(name)
    return acts[::-1],B,E

def actstr(d): return ' '.join(DIRACT[x] for x in d)
