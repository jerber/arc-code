"""Build a world overlay from logged level-6 boards with known camera offsets."""
import numpy as np,json
R=json.load(open('mined.json')); B=np.load('mined_boards.npy')
CAM={n:c for n,c,d,a in json.load(open('cam6.json'))}
W=200
def build(nmin,nmax):
    world=-np.ones((64,W),dtype=np.int16)
    for i,r in enumerate(R):
        if r['lvl']!=6: continue
        n=r['n']
        if not(nmin<=n<=nmax): continue
        cam=CAM[n]; a=B[i]
        world[1:64,cam:cam+64]=a[1:64,:]
    return world
def cells(world):
    """classify each lattice cell"""
    out={}
    for c in range((W)//6):
        for r in range(11):
            x0,y0=6*c,6*r
            if x0+4>W or y0+4>64 or y0<1: continue
            v=world[y0:y0+4,x0:x0+4]
            if (v<0).any(): out[(c,r)]='?'; continue
            s=set(v.flatten().tolist())
            ring=[]
            if x0>=1 and y0>=1 and x0+4<W and y0+4<64:
                ring=list(world[y0-1,x0-1:x0+5])+list(world[y0+4,x0-1:x0+5])+list(world[y0-1:y0+5,x0-1])+list(world[y0-1:y0+5,x0+4])
            sh = 0xb in ring
            if s=={10}: out[(c,r)]=' '
            elif 0xf in s or 7 in s: out[(c,r)]='V' if sh else 'P'
            elif 8 in s: out[(c,r)]='R' if not sh else 'r'
            elif 0xe in s: out[(c,r)]='O' if not sh else 'S'
            elif sh: out[(c,r)]='s'
            elif s<={1,0,2,3}: out[(c,r)]='.' if 1 in s else 'o'
            elif 5 in s and s<={5,0,9,10,0xc,0xb}: out[(c,r)]='+'
            else: out[(c,r)]='#'
    return out
def show(out,lo=0,hi=W//6):
    print('    '+''.join(str(c//10) for c in range(lo,hi)))
    print('    '+''.join(str(c%10) for c in range(lo,hi)))
    for r in range(0,11):
        print('%3d %s'%(r,''.join(out.get((c,r),'?') for c in range(lo,hi))))
if __name__=='__main__':
    import sys
    a,b=int(sys.argv[1]),int(sys.argv[2])
    w=build(a,b); show(cells(w))
