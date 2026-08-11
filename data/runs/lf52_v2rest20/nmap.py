"""numpy world mapper: align every view of a level into a big canvas."""
import numpy as np, parse, json, sys
BG=10  # 'a'
def to_arr(rows):
    return np.array([[int(c,16) for c in r] for r in rows],dtype=np.int16)
class World:
    def __init__(self,size=(400,700),off=(200,200)):
        self.H,self.W=size; self.oy,self.ox=off
        self.c=np.full((self.H,self.W),-1,dtype=np.int16)
    def paste(self,a,ox,oy):
        y0,x0=oy+self.oy, ox+self.ox
        self.c[y0+1:y0+64, x0:x0+64]=a[1:64,:]
    def fit(self,a,cx,cy,rad=60,ystep=1):
        ys,xs=np.nonzero(a[1:64,:]!=BG); ys=ys+1
        vals=a[ys,xs]
        best=None
        for oy in range(cy-rad,cy+rad+1,ystep):
            yy=ys+oy+self.oy
            if yy.min()<0 or yy.max()>=self.H: continue
            for ox in range(cx-rad,cx+rad+1):
                xx=xs+ox+self.ox
                if xx.min()<0 or xx.max()>=self.W: continue
                cv=self.c[yy,xx]
                known=cv>=0
                if known.sum()<200: continue
                same=int(((cv==vals)&known).sum()); diff=int(known.sum())-same
                sc=same-4*diff
                if best is None or sc>best[0]: best=(sc,ox,oy,same,diff)
        return best
def build(lo,hi,verbose=True):
    bs=parse.blocks(); w=World()
    a=to_arr(bs[lo][1]); w.paste(a,0,0)
    offs={lo:(0,0)}; ox,oy=0,0
    for i in range(lo+1,hi+1):
        a=to_arr(bs[i][1])
        f=w.fit(a,ox,oy,rad=20)
        if f is None or f[4]>max(20,f[3]//5):
            f2=w.fit(a,ox,oy,rad=120)
            if f2 and (f is None or f2[0]>f[0]): f=f2
        if f is None:
            if verbose: print('view',i,'NO FIT'); continue
        sc,nox,noy,same,diff=f
        if verbose: print('view %d %-18s off (%d,%d) same %d diff %d'%(i,bs[i][0].split('|')[3].strip()[:18],nox,noy,same,diff))
        ox,oy=nox,noy; offs[i]=(ox,oy); w.paste(a,ox,oy)
    np.save('canvas.npy',w.c)
    json.dump({'offs':{str(k):list(v) for k,v in offs.items()},'OX':w.ox,'OY':w.oy},open('offsets.json','w'))
    ys,xs=np.nonzero(w.c>=0)
    print('world known: x %d..%d y %d..%d'%(xs.min()-w.ox,xs.max()-w.ox,ys.min()-w.oy,ys.max()-w.oy))
    return w
if __name__=='__main__':
    build(int(sys.argv[1]),int(sys.argv[2]))
