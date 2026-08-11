"""Mine logs.txt: per-action camera shift (dx,dy) between consecutive final boards."""
import re,sys,numpy as np,parse,json
BG=10
def arr(rows): return np.array([[int(c,16) for c in r] for r in rows],dtype=np.int16)
def shift(a,b,rng=24):
    # find (dx,dy) so that b[y,x] == a[y+dy, x+dx] for overlap (camera moved by dx)
    best=None
    A=a[1:,:]; B=b[1:,:]
    for dy in range(-4,5):
        for dx in range(-rng,rng+1):
            ys=slice(max(0,dy),min(63,63+dy)); yt=slice(max(0,-dy),min(63,63-dy))
            xs=slice(max(0,dx),min(64,64+dx)); xt=slice(max(0,-dx),min(64,64-dx))
            sa=A[ys,xs]; sb=B[yt,xt]
            if sa.size<64*30: continue
            same=int((sa==sb).sum()); tot=sa.size
            sc=same/tot
            if best is None or sc>best[0]: best=(sc,dx,dy,tot)
    return best
def main():
    bs=parse.blocks()
    rows=[]
    prev=None
    for hdr,rw in bs:
        if len(rw)!=64: 
            prev=None; continue
        m=re.match(r'action (\d+) \| level (\d+) attempt (\d+) \| score (\d+) \| (.*?)(?: \| step.*)?$',hdr)
        a=arr(rw)
        rec=dict(n=int(m.group(1)),lvl=int(m.group(2)),att=int(m.group(3)),score=int(m.group(4)),act=m.group(5))
        if prev is not None and prev['lvl']==rec['lvl'] and prev['att']==rec['att']:
            sc,dx,dy,tot=shift(prev['a'],a)
            rec['dx'],rec['dy'],rec['fit']=dx,dy,round(sc,3)
        else:
            rec['dx'],rec['dy'],rec['fit']=None,None,None
        rec['a']=a
        rows.append(rec); prev=rec
    np.save('mined_boards.npy',np.array([r['a'] for r in rows]))
    json.dump([{k:v for k,v in r.items() if k!='a'} for r in rows],open('mined.json','w'))
    print('blocks',len(rows))
main()
