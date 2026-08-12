"""Per-view classification merged into world structure: cells, track, conn, tconn."""
import parse, json, collections
def classify(vals):
    """vals = 16 ints of a 4x4 block, row-major"""
    s=set(vals); corners=[vals[0],vals[3],vals[12],vals[15]]
    if s<={1,0xe,2} and all(v in (1,2) for v in corners): return 'peg' if 0xe in s else 'cell'
    if s<={0xc,0xe} and all(v==0xc for v in corners): return 'shpeg' if 0xe in s else 'sh'
    if 0xf in s: return 'pivot'
    return None
def build(lo,hi):
    bs=parse.blocks()
    offs=json.load(open('offsets.json'))['offs']
    votes=collections.defaultdict(set)     # world cell -> {'cell','track','sh',...}
    gap=collections.defaultdict(set)       # (a,b) -> {'open','wall'}
    for i in range(lo,hi+1):
        if str(i) not in offs: continue
        ox,oy=offs[str(i)]
        rows=bs[i][1]
        g=[[int(c,16) for c in r] for r in rows]
        def blk(c,r):
            x0,y0=6*c-ox,6*r-oy
            if not(0<=x0<=60 and 1<=y0<=60): return None
            return [g[y0+j][x0+i2] for j in range(4) for i2 in range(4)]
        for c in range(-3,45):
            for r in range(-3,30):
                v=blk(c,r)
                if v is None: continue
                k=classify(v)
                if k=='pivot': votes[(c,r)].add('pivot')
                elif k in ('cell','peg'): votes[(c,r)].add('cell')
                elif k in ('sh','shpeg'): votes[(c,r)].add('sh')
                elif all(v[j]==5 for j in (5,6,9,10)): votes[(c,r)].add('track')
                else: votes[(c,r)].add('none')
        # gaps
        for c in range(-3,45):
            for r in range(-3,30):
                x0,y0=6*c-ox,6*r-oy
                for dc,dr in ((1,0),(0,1)):
                    if dc:
                        if not(0<=x0 and x0+5<=63 and 1<=y0 and y0+3<=63): continue
                        px=[g[y0+j][x0+4+i2] for j in range(4) for i2 in range(2)]
                        pt=[g[y0+j][x0+4+i2] for j in (1,2) for i2 in range(2)]
                    else:
                        if not(0<=x0 and x0+3<=63 and 1<=y0 and y0+5<=63): continue
                        px=[g[y0+4+j][x0+i2] for j in range(2) for i2 in range(4)]
                        pt=[g[y0+4+j][x0+i2] for j in range(2) for i2 in (1,2)]
                    key=((c,r),(c+dc,r+dr))
                    gap[key].add('open' if 5 not in px else 'wall')
                    if all(v==5 for v in pt): gap[key].add('pipe')
    pivots={k for k,v in votes.items() if 'pivot' in v}
    cells={k for k,v in votes.items() if 'cell' in v}-pivots
    track={k for k,v in votes.items() if 'cell' not in v and ('track' in v or 'sh' in v)}
    conn=set()
    for (a,b),v in gap.items():
        if a in cells and b in cells and 'open' in v: conn|={(a,b),(b,a)}
    tconn=set()
    for (a,b),v in gap.items():
        if 'pipe' not in v: continue
        if a in track|cells and b in track|cells and not(a in cells and b in cells):
            tconn|={(a,b),(b,a)}
    return cells,track,conn,tconn,set(votes),pivots
if __name__=='__main__':
    import sys
    lo,hi=int(sys.argv[1]),int(sys.argv[2])
    cells,track,conn,tconn,known,pivots=build(lo,hi)
    json.dump({'cells':sorted(map(list,cells)),'track':sorted(map(list,track)),
               'conn':sorted([list(a)+list(b) for a,b in conn]),
               'tconn':sorted([list(a)+list(b) for a,b in tconn]),
               'known':sorted(map(list,known)),'pivots':sorted(map(list,pivots))},open('structure.json','w'))
    cs=[c for c,r in cells|track]; rs=[r for c,r in cells|track]
    print('cells',len(cells),'track',len(track))
    print('    '+''.join(str(c%10) for c in range(min(cs)-1,max(cs)+2)))
    for r in range(min(rs)-1,max(rs)+2):
        line=''
        for c in range(min(cs)-1,max(cs)+2):
            k=(c,r)
            line += ('P' if k in pivots else '#') if (k in cells or k in pivots) else ('+' if k in track else ('?' if k not in known else '.'))
        print('%3d %s'%(r,line))
    import collections
    d=[(t,n) for t in track for dd in ((1,0),(-1,0),(0,1),(0,-1)) for n in [(t[0]+dd[0],t[1]+dd[1])] if n in cells]
    print('docks',d)
