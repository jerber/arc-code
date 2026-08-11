"""Current board -> world state using canvas.npy + structure.json (numpy fit)."""
import numpy as np, parse, json, sys
C=np.load('canvas.npy'); OFFS=json.load(open('offsets.json')); OX,OY=OFFS['OX'],OFFS['OY']
S=json.load(open('structure.json'))
CELLS={tuple(x) for x in S['cells']}; PIVOTS={tuple(x) for x in S['pivots']}
TRACK={tuple(x) for x in S['track']}; KNOWN={tuple(x) for x in S['known']}
CONN={((a,b),(c,d)) for a,b,c,d in S['conn']}; TCONN={((a,b),(c,d)) for a,b,c,d in S['tconn']}
BG=10
def to_arr(rows): return np.array([[int(c,16) for c in r] for r in rows],dtype=np.int16)
def fit(a,rad=None):
    ys,xs=np.nonzero(a[1:64,:]!=BG); ys=ys+1; vals=a[ys,xs]
    H,W=C.shape; best=None
    for oy in range(-OY,H-OY-64):
        yy=ys+oy+OY
        if yy.min()<0 or yy.max()>=H: continue
        for ox in range(-OX,W-OX-64):
            xx=xs+ox+OX
            if xx.min()<0 or xx.max()>=W: continue
            cv=C[yy,xx]; known=cv>=0
            if known.sum()<200: continue
            same=int(((cv==vals)&known).sum()); diff=int(known.sum())-same
            sc=same-4*diff
            if best is None or sc>best[0]: best=(sc,ox,oy,same,diff)
    return best
def state(rows=None):
    if rows is None: rows=parse.last()[1]
    a=to_arr(rows); f=fit(a); ox,oy=f[1],f[2]
    pegs=set(); reds=set(); sh={}
    for c in range((ox)//6-2,(ox+64)//6+2):
        for r in range((oy)//6-2,(oy+64)//6+2):
            x0,y0=6*c-ox,6*r-oy
            if not(0<=x0<=60 and 1<=y0<=60): continue
            v=a[y0:y0+4,x0:x0+4]; s=set(v.flatten().tolist())
            corners=[v[0,0],v[0,3],v[3,0],v[3,3]]
            ring=[]
            if x0>=1 and y0>=1 and x0+4<64 and y0+4<64:
                ring=list(a[y0-1,x0-1:x0+5])+list(a[y0+4,x0-1:x0+5])+list(a[y0-1:y0+5,x0-1])+list(a[y0-1:y0+5,x0+4])
            if 0xb in ring:
                sh[(c,r)]='pivot' if (0xf in s or 7 in s) else ('red' if 8 in s else ('peg' if 0xe in s else None))
            elif 0xf in s or 7 in s: continue
            elif s<={1,0xe,2,8,3} and all(x in (1,2,3) for x in corners):
                if 8 in s: reds.add((c,r))
                elif 0xe in s: pegs.add((c,r))
    return (ox,oy),pegs,sh,f,reds
def show(off,pegs,sh,reds=()):
    allk=CELLS|PIVOTS|TRACK|set(pegs)|set(sh)
    cs=[c for c,r in allk]; rs=[r for c,r in allk]
    print('offset',off,'pegs',sorted(pegs),'shuttles',sh)
    print('     '+''.join(str(c%10) for c in range(min(cs)-1,max(cs)+2)))
    for r in range(min(rs)-1,max(rs)+2):
        line=''
        for c in range(min(cs)-1,max(cs)+2):
            k=(c,r)
            if k in sh: line+={'peg':'S','pivot':'V',None:'s'}[sh[k]]
            elif k in pegs: line+='O'
            elif k in reds: line+='R'
            elif k in PIVOTS: line+='P'
            elif k in CELLS: line+='.'
            elif k in TRACK: line+='+'
            elif k not in KNOWN: line+='?'
            else: line+=' '
        print('%4d %s'%(r,line))
if __name__=='__main__':
    off,pegs,sh,f,reds=state(); print('fit',f,'reds',sorted(reds)); show(off,pegs,sh,reds)
