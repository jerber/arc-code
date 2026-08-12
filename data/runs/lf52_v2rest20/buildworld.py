"""Stitch every view of the current level into worldmap.txt (incremental offsets)."""
import parse, sys, json, os
W,H,OFF=260,200,80
def blank(): return [['?']*W for _ in range(H)]
def paste(canvas,rows,ox,oy):
    for y in range(1,64):
        for x in range(64):
            cx,cy=x+ox+OFF,y+oy+OFF
            if 0<=cx<W and 0<=cy<H: canvas[cy][cx]=rows[y][x]
def score(canvas,rows,ox,oy):
    s=d=0
    for y in range(1,64):
        cy=y+oy+OFF
        if not(0<=cy<H): continue
        crow=canvas[cy]
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
def fit(canvas,rows,cx,cy,rad=10):
    best=None
    for oy in range(cy-rad,cy+rad+1):
        for ox in range(cx-rad,cx+rad+1):
            s,d=score(canvas,rows,ox,oy)
            if s+d<250: continue
            sc=s-4*d
            if best is None or sc>best[0]: best=(sc,ox,oy,s,d)
    return best
def build(lo,hi,verbose=True):
    bs=parse.blocks()
    canvas=blank()
    paste(canvas,bs[lo][1],0,0)
    ox,oy=0,0; offs={lo:(0,0)}
    for i in range(lo+1,hi+1):
        rows=bs[i][1]
        f=fit(canvas,rows,ox,oy)
        if f is None or f[4]>f[3]//4:
            f2=fit(canvas,rows,ox,oy,rad=40)
            if f2 and (f is None or f2[0]>f[0]): f=f2
        if f is None: continue
        _,nox,noy,s,d=f
        if verbose: print('view',i,bs[i][0].split('|')[3].strip()[:16],'off',nox,noy,'s',s,'d',d)
        ox,oy=nox,noy; offs[i]=(ox,oy)
        paste(canvas,rows,ox,oy)
    open('worldmap.txt','w').write('\n'.join(''.join(r) for r in canvas))
    json.dump({'offs':{str(k):v for k,v in offs.items()},'OFF':OFF},open('offsets.json','w'))
    xs=[x for y in range(H) for x in range(W) if canvas[y][x]!='?']
    ys=[y for y in range(H) for x in range(W) if canvas[y][x]!='?']
    print('world known: x %d..%d  y %d..%d'%(min(xs)-OFF,max(xs)-OFF,min(ys)-OFF,max(ys)-OFF))
    return canvas
if __name__=='__main__':
    build(int(sys.argv[1]),int(sys.argv[2]))
