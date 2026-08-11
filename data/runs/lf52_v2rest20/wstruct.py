"""Build world structure (cells, pivots, track, conn, tconn) from all views + offsets."""
import numpy as np, parse, json, collections, sys
def classify(v,ring=None):
    s=set(v.flatten().tolist()); corners=[v[0,0],v[0,3],v[3,0],v[3,3]]
    if ring is not None and 0xb in ring:          # yellow frame => shuttle
        return 'shpiv' if (0xf in s or 7 in s) else ('shpeg' if 0xe in s else 'sh')
    if 0xf in s or 7 in s: return 'pivot'
    if s<={1,0xe,2,8} and all(x in (1,2) for x in corners): return 'peg' if (0xe in s or 8 in s) else 'cell'
    if s<={0xc,0xe} and all(x==0xc for x in corners): return 'shpeg' if 0xe in s else 'sh'
    return None
def build(lo,hi):
    bs=parse.blocks(); offs=json.load(open('offsets.json'))['offs']
    votes=collections.defaultdict(set); gap=collections.defaultdict(set)
    for i in range(lo,hi+1):
        if str(i) not in offs: continue
        ox,oy=offs[str(i)]
        g=np.array([[int(c,16) for c in r] for r in bs[i][1]],dtype=np.int16)
        cmin=(ox)//6-2; cmax=(ox+64)//6+2; rmin=(oy)//6-2; rmax=(oy+64)//6+2
        for c in range(cmin,cmax+1):
            for r in range(rmin,rmax+1):
                x0,y0=6*c-ox,6*r-oy
                if not(0<=x0<=60 and 1<=y0<=60): continue
                v=g[y0:y0+4,x0:x0+4]
                ring=[]
                if x0>=1 and y0>=1 and x0+4<64 and y0+4<64:
                    ring=list(g[y0-1,x0-1:x0+5])+list(g[y0+4,x0-1:x0+5])+list(g[y0-1:y0+5,x0-1])+list(g[y0-1:y0+5,x0+4])
                k=classify(v,ring)
                if k=='pivot': votes[(c,r)].add('pivot')
                elif k in ('cell','peg'): votes[(c,r)].add('cell')
                elif k in ('sh','shpeg','shpiv'): votes[(c,r)].add('sh')
                elif (v[1,1]==5 and v[1,2]==5 and v[2,1]==5 and v[2,2]==5): votes[(c,r)].add('track')
                else: votes[(c,r)].add('none')
                for dc,dr in ((1,0),(0,1)):
                    if dc and x0+5<=63:
                        px=g[y0:y0+4,x0+4:x0+6]; pt=g[y0+1:y0+3,x0+4:x0+6]
                    elif dr and y0+5<=63:
                        px=g[y0+4:y0+6,x0:x0+4]; pt=g[y0+4:y0+6,x0+1:x0+3]
                    else: continue
                    key=((c,r),(c+dc,r+dr))
                    gap[key].add('open' if 5 not in set(px.flatten().tolist()) else 'wall')
                    if (pt==5).all(): gap[key].add('pipe')
                    if 0xb in set(px.flatten().tolist()): gap[key].add('framed')
    pivots={k for k,v in votes.items() if 'pivot' in v}
    cells={k for k,v in votes.items() if 'cell' in v}-pivots
    track={k for k,v in votes.items() if 'cell' not in v and 'pivot' not in v and ('track' in v or 'sh' in v)}
    occ=cells|pivots
    conn=set()
    for (a,b),v in gap.items():
        if a in occ and b in occ and 'open' in v: conn|={(a,b),(b,a)}
    tconn=set()
    for (a,b),v in gap.items():
        if ('pipe' in v or 'framed' in v) and a in track|cells and b in track|cells and not(a in cells and b in cells):
            tconn|={(a,b),(b,a)}
    return dict(cells=cells,pivots=pivots,track=track,conn=conn,tconn=tconn,known=set(votes))
def save(S):
    json.dump({k:(sorted([list(a)+list(b) for a,b in v]) if k in ('conn','tconn') else sorted(map(list,v)))
               for k,v in S.items()},open('structure.json','w'))
def show(S):
    cells,pivots,track,known=S['cells'],S['pivots'],S['track'],S['known']
    allk=cells|pivots|track
    cs=[c for c,r in allk]; rs=[r for c,r in allk]
    print('cells',len(cells),'pivots',len(pivots),'track',len(track))
    print('     '+''.join(str(c%10) for c in range(min(cs)-1,max(cs)+2)))
    for r in range(min(rs)-1,max(rs)+2):
        line=''
        for c in range(min(cs)-1,max(cs)+2):
            k=(c,r)
            line += 'P' if k in pivots else ('#' if k in cells else ('+' if k in track else ('?' if k not in known else '.')))
        print('%4d %s'%(r,line))
if __name__=='__main__':
    S=build(int(sys.argv[1]),int(sys.argv[2])); save(S); show(S)
    d=[(t,n) for t in S['track'] for dd in ((1,0),(-1,0),(0,1),(0,-1)) for n in [(t[0]+dd[0],t[1]+dd[1])] if n in S['cells']|S['pivots']]
    print('docks',sorted(d))
