import json,os,re
from collections import Counter,deque
from board import grid,comps

class View:
    def __init__(self,path):
        g=grid(path); self.g=g
        tiles=[c for c in comps(g,set('1e23')) if len(c)>=8]
        if tiles:
            self.ox=Counter(min(p[0] for p in c)%6 for c in tiles).most_common(1)[0][0]
            self.oy=Counter(min(p[1] for p in c)%6 for c in tiles).most_common(1)[0][0]
        else:
            self.ox=self.oy=0
        self.cls={}; self.peg=set(); self.shut={}
        X0=-(self.ox//6)-1
        for Y in range(-1,12):
            for X in range(-1,12):
                x0,y0=self.ox+6*X,self.oy+6*Y
                if x0<0 or y0<0 or x0+3>63 or y0+3>63: continue
                c=set(g[y0+dy][x0+dx] for dy in range(4) for dx in range(4))
                ring=[]
                for dx in range(-1,5):
                    for dy in range(-1,5):
                        if dx in (-1,4) or dy in (-1,4):
                            xx,yy=x0+dx,y0+dy
                            ring.append(g[yy][xx] if 0<=xx<64 and 0<=yy<64 else 'a')
                isshut = ring.count('b')>=12
                if isshut:
                    k='TRACK'
                    self.shut[(X,Y)]='SWALL' if 'f' in c else ('SPEG' if 'e' in c else 'SHUTTLE')
                elif 'f' in c and '7' in c: k='WALL'
                elif 'c' in c:
                    k='TRACK'; self.shut[(X,Y)]='SPEG' if 'e' in c else 'SHUTTLE'
                elif c<=set('1e23'):
                    k='CELL'
                    if 'e' in c: self.peg.add((X,Y))
                elif c=={'a'}: k='EMPTY'
                elif all(g[y0+r][x0+cc]=='5' for r in (1,2) for cc in (1,2)): k='TRACK'
                else: k=None
                if k: self.cls[(X,Y)]=k

class World:
    def __init__(self,path='world.json'):
        self.path=path
        if os.path.exists(path):
            d=json.load(open(path))
            self.map={tuple(map(int,k.split(','))):v for k,v in d['map'].items()}
        else: self.map={}
    def save(self):
        json.dump({'map':{f'{k[0]},{k[1]}':v for k,v in self.map.items()}},open(self.path,'w'))
    def align(self,v):
        if not self.map: return (0,0)
        best=None
        for dx in range(-30,31):
            for dy in range(-30,31):
                m=mm=0
                for (X,Y),k in v.cls.items():
                    w=self.map.get((X+dx,Y+dy))
                    if w is None: continue
                    if w==k: m+=1
                    else: mm+=1
                if m<6: continue
                sc=m-4*mm
                if best is None or sc>best[0]: best=(sc,dx,dy,m,mm)
        return (best[1],best[2]) if best else (0,0)
    def merge(self,v,off):
        dx,dy=off
        for (X,Y),k in v.cls.items():
            w=(X+dx,Y+dy)
            if k=='EMPTY':
                if w not in self.map: self.map[w]='EMPTY'
            else: self.map[w]=k
        self.save()
    def dump(self,pegs=(),shut=()):
        if not self.map: print('(empty)'); return
        xs=[k[0] for k in self.map]; ys=[k[1] for k in self.map]
        sym={'CELL':'.','WALL':'W','TRACK':'=','EMPTY':' '}
        print('    '+''.join(str(x%10) for x in range(min(xs),max(xs)+1)))
        for Y in range(min(ys),max(ys)+1):
            r=''
            for X in range(min(xs),max(xs)+1):
                if (X,Y) in pegs: r+='P'
                elif (X,Y) in shut: r+='S'
                else: r+=sym.get(self.map.get((X,Y)),'?')
            print(f'{Y:3d} '+r)
