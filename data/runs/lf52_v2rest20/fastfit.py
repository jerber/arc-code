import numpy as np, json
C=np.load('canvas.npy'); O=json.load(open('offsets.json')); OX,OY=O['OX'],O['OY']
H,W=C.shape
print('canvas',C.shape,'OX,OY',OX,OY) if __name__=='__main__' else None
def fitx(a):
    """return best ox with dy=0 (screen (x,y) -> canvas (x+ox+OX, y+OY))"""
    ys,xs=np.nonzero(a[1:64,:]!=10); ys=ys+1; vals=a[ys,xs]
    best=None
    yy=ys+OY
    if yy.min()<0 or yy.max()>=H: return None
    for ox in range(-OX,W-OX-64):
        xx=xs+ox+OX
        if xx.min()<0 or xx.max()>=W: continue
        cv=C[yy,xx]; known=cv>=0
        if known.sum()<200: continue
        same=int(((cv==vals)&known).sum()); diff=int(known.sum())-same
        sc=same-4*diff
        if best is None or sc>best[0]: best=(sc,ox,same,diff)
    return best
