"""Current board -> world-coordinate state, using worldmap.txt as the reference."""
import parse, wparse, json, sys
OFF=wparse.OFF
CANVAS=[list(l) for l in open('worldmap.txt').read().split('\n')]
H=len(CANVAS); W=len(CANVAS[0])
CELLS,TRACK,CONN,TCONN,KNOWN=wparse.parse(wparse.load())
def score(rows,ox,oy):
    s=d=0
    for y in range(1,64):
        cy=y+oy+OFF
        if not(0<=cy<H): continue
        crow=CANVAS[cy]
        for x in range(64):
            cx=x+ox+OFF
            if not(0<=cx<W): continue
            c=crow[cx]
            if c=='?': continue
            r=rows[y][x]
            if c=='a' and r=='a': continue
            if c==r: s+=1
            else: d+=1
    return s,d
def fit(rows,lo=-10,hi=140):
    best=None
    for oy in range(-10,11,1):
        for ox in range(lo,hi):
            s,d=score(rows,ox,oy)
            if s+d<250: continue
            sc=s-4*d
            if best is None or sc>best[0]: best=(sc,ox,oy,s,d)
    return best
def state(rows=None,off=None):
    if rows is None: rows=parse.last()[1]
    if off is None:
        f=fit(rows); off=(f[1],f[2])
    ox,oy=off
    g=[[int(c,16) for c in r] for r in rows]
    pegs=set(); sh={}
    for c in range(-3,40):
        for r in range(-3,30):
            x0,y0=6*c-ox, 6*r-oy
            if not(0<=x0<=60 and 0<=y0<=60): continue
            vals=[g[y0+j][x0+i] for j in range(4) for i in range(4)]
            s=set(vals)
            if s<={1,0xe,2}:
                if 0xe in s: pegs.add((c,r))
            elif s<={0xc,0xe}: sh[(c,r)]=(0xe in s)
    return (ox,oy),pegs,sh
def show(off,pegs,sh):
    cs=[c for c,r in CELLS|TRACK|set(pegs)|set(sh)]; rs=[r for c,r in CELLS|TRACK|set(pegs)|set(sh)]
    print('offset',off,'pegs',len(pegs),sorted(pegs),'shuttles',sh)
    print('    '+''.join(str(c%10) for c in range(min(cs)-1,max(cs)+2)))
    for r in range(min(rs)-1,max(rs)+2):
        line=''
        for c in range(min(cs)-1,max(cs)+2):
            k=(c,r)
            if k in sh: line+='S' if sh[k] else 's'
            elif k in pegs: line+='O'
            elif k in CELLS: line+='.'
            elif k in TRACK: line+='+'
            elif k not in KNOWN: line+='?'
            else: line+=' '
        print('%3d %s'%(r,line))
if __name__=='__main__':
    off,pegs,sh=state(); show(off,pegs,sh)
