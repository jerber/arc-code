"""Structural parse of the merged world canvas: cells, walls, track."""
import json,os
OFF=json.load(open('offsets.json')).get('OFF',40) if os.path.exists('offsets.json') else 40
def load(path='worldmap.txt'):
    canvas=open(path).read().split('\n')
    g=[[int(c,16) if c in '0123456789abcdef' else -1 for c in row] for row in canvas]
    return g
def px(c,r): return (6*c+OFF, 6*r+OFF)
def parse(g):
    H=len(g); W=len(g[0])
    def at(x,y):
        return g[y][x] if 0<=x<W and 0<=y<H else -1
    cells=set(); track=set(); known=set()
    for c in range(-3,40):
        for r in range(-3,30):
            x0,y0=px(c,r)
            vals=[at(x0+i,y0+j) for j in range(4) for i in range(4)]
            if -1 in vals: continue
            known.add((c,r))
            s=set(vals)
            if s<={1,0xe,2} or s<={0xc,0xe}: cells.add((c,r))
            elif all(at(x0+i,y0+j)==5 for j in (1,2) for i in (1,2)): track.add((c,r))
    conn=set()
    for (c,r) in cells:
        for dc,dr in((1,0),(0,1)):
            n=(c+dc,r+dr)
            if n not in cells: continue
            x0,y0=px(c,r)
            gap=[at(x0+4+i,y0+j) for j in range(4) for i in range(2)] if dc else \
                [at(x0+i,y0+4+j) for j in range(2) for i in range(4)]
            if 5 not in gap: conn|={((c,r),n),(n,(c,r))}
    tconn=set()
    for (c,r) in track|cells:
        for dc,dr in((1,0),(0,1)):
            n=(c+dc,r+dr)
            if n not in track|cells: continue
            if (c,r) in cells and n in cells: continue
            x0,y0=px(c,r)
            gap=[at(x0+4+i,y0+j) for j in (1,2) for i in range(2)] if dc else \
                [at(x0+i,y0+4+j) for j in range(2) for i in (1,2)]
            if all(v==5 for v in gap): tconn|={((c,r),n),(n,(c,r))}
    return cells,track,conn,tconn,known
if __name__=='__main__':
    g=load(); cells,track,conn,tconn,known=parse(g)
    print('cells',len(cells),'track',len(track))
    cs=[c for c,r in cells|track]; rs=[r for c,r in cells|track]
    print('    '+''.join(str(c%10) for c in range(min(cs)-1,max(cs)+2)))
    for r in range(min(rs)-1,max(rs)+2):
        line=''
        for c in range(min(cs)-1,max(cs)+2):
            k=(c,r)
            line += '#' if k in cells else ('+' if k in track else ('?' if k not in known else ' '))
        print('%3d %s'%(r,line))
    print('conns',len(conn)//2,'tconns',len(tconn)//2)
    # print components of cells
    seen=set(); comps=[]
    for k in cells:
        if k in seen: continue
        st=[k]; comp={k}; seen.add(k)
        while st:
            a=st.pop()
            for b in [n for (x,n) in conn if x==a]:
                if b not in seen: seen.add(b); comp.add(b); st.append(b)
        comps.append(sorted(comp))
    for i,comp in enumerate(comps): print('region',i,len(comp),comp)
    # docks: track cell adjacent to a cell
    docks=[(t,(t[0]+d[0],t[1]+d[1])) for t in track for d in ((1,0),(-1,0),(0,1),(0,-1)) if (t[0]+d[0],t[1]+d[1]) in cells]
    print('docks:',docks)
