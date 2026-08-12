"""Per-action peg map in world coords for level 6."""
import numpy as np,json
R=json.load(open('mined.json')); B=np.load('mined_boards.npy')
CAM={n:c for n,c,d,a in json.load(open('cam6.json'))}
def pegs(a,cam):
    """return dict cell->char for visible lattice cells"""
    out={}
    for c in range(cam//6-1,(cam+64)//6+1):
        x0=6*c-cam
        if x0<0 or x0+4>64: continue
        for r in range(1,11):
            y0=6*r
            if y0+4>64: continue
            v=a[y0:y0+4,x0:x0+4]; s=set(v.flatten().tolist())
            ring=[]
            if x0>=1 and x0+4<64 and y0+4<64:
                ring=list(a[y0-1,x0-1:x0+5])+list(a[y0+4,x0-1:x0+5])+list(a[y0-1:y0+5,x0-1])+list(a[y0-1:y0+5,x0+4])
            sh=0xb in ring
            if s=={10}: ch=' '
            elif 0xf in s or 7 in s: ch='V' if sh else 'P'
            elif 8 in s: ch='r' if sh else 'R'
            elif 0xe in s: ch='S' if sh else 'O'
            elif sh: ch='s'
            elif s<={1,0,2,3}: ch='.' if 1 in s else 'o'
            elif 5 in s: ch='+'
            else: ch='#'
            out[(c,r)]=ch
    return out
def series(nmin,nmax):
    prev=None
    for i,rec in enumerate(R):
        if rec['lvl']!=6: continue
        n=rec['n']
        if not(nmin<=n<=nmax): continue
        p=pegs(B[i],CAM[n])
        if prev is not None:
            ch={k:(prev.get(k),v) for k,v in p.items() if k in prev and prev[k]!=v}
            yield n,rec['act'],CAM[n],ch
        prev=p
if __name__=='__main__':
    import sys
    a,b=int(sys.argv[1]),int(sys.argv[2])
    for n,act,cam,ch in series(a,b):
        if ch: print(n,act,'cam',cam,{k:'%s->%s'%v for k,v in sorted(ch.items())})
