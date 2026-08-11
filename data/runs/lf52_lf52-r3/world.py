import re,sys,json,os
HOLE=set('123e8')
CACHE='offsets.json'
def frames(path='logs.txt'):
    txt=open(path).read(); out=[]
    for p in re.split(r'\n(?=={10,})',txt):
        m=re.search(r'action (\d+) \| level (\d+) attempt (\d+) \| score (\d+) \| (.*?)(?:\n|$)',p)
        if not m: continue
        i=p.rfind('[final]'); j=p.rfind('[anim')
        if j>i: i=j
        rows=[l for l in p[i:].split('\n')[1:] if re.fullmatch(r'[0-9a-f]{64}',l)][:64]
        if len(rows)==64:
            out.append(dict(action=int(m.group(1)),level=int(m.group(2)),attempt=int(m.group(3)),
                            score=int(m.group(4)),what=m.group(5).strip(),rows=rows))
    return out

import numpy as np
def arr(rows): return np.frombuffer(''.join(rows).encode(),dtype=np.uint8).reshape(64,64)

def rel_shift(a,b,rad=48):
    """find (dx,dy) s.t. a[y][x] == b[y+dy][x+dx]; returns shift and score"""
    A=arr(a); B=arr(b)
    best=(-1,0,0,0)
    for dy in range(-rad,rad+1):
        ay0=max(0,-dy); ay1=min(64,64-dy)
        if ay1-ay0<16: continue
        for dx in range(-rad,rad+1):
            ax0=max(0,-dx); ax1=min(64,64-dx)
            if ax1-ax0<16: continue
            sub_a=A[ay0:ay1,ax0:ax1]
            sub_b=B[ay0+dy:ay1+dy,ax0+dx:ax1+dx]
            tot=sub_a.size
            if tot<900: continue
            same=int(np.count_nonzero(sub_a==sub_b))
            sc=same/tot
            if sc>best[0]+1e-9 or (abs(sc-best[0])<1e-9 and abs(dx)+abs(dy)<abs(best[1])+abs(best[2])):
                best=(sc,dx,dy,tot)
    return best[1],best[2],best[0]

def parse_frame(rows):
    cand={};shut={}
    for y in range(0,61):
        for x in range(0,61):
            blk=''.join(rows[y+dy][x:x+4] for dy in range(4))
            r=[]
            for i in range(-1,5):
                if y-1>=0 and 0<=x+i<64: r.append(rows[y-1][x+i])
                if y+4<64 and 0<=x+i<64: r.append(rows[y+4][x+i])
            for dy in range(4):
                if x-1>=0: r.append(rows[y+dy][x-1])
                if x+4<64: r.append(rows[y+dy][x+4])
            if all(ch in HOLE for ch in blk):
                if not any(ch in set('12e8') for ch in r):
                    cand[(x,y)]='R' if '8' in blk else ('P' if 'e' in blk else '.')
            elif all(ch in set('ce') for ch in blk) and 'c' in blk:
                if all(ch=='b' for ch in r): shut[(x,y)]='P' if 'e' in blk else '.'
    # keep only dominant lattice phase
    if cand:
        from collections import Counter
        ph=Counter((x%6,y%6) for x,y in cand).most_common(1)[0][0]
        cand={k:v for k,v in cand.items() if (k[0]%6,k[1]%6)==ph}
    return cand,shut

def track_nodes(rows):
    ns=set()
    for y in range(0,61):
        for x in range(0,61):
            h=all(rows[y+1][xx]=='5' and rows[y+2][xx]=='5' for xx in range(x,x+4))
            v=all(rows[yy][x+1]=='5' and rows[yy][x+2]=='5' for yy in range(y,y+4))
            if h or v: ns.add((x,y))
    return ns

def canvas_match(canv,mask,ox0,oy0,rows,cx,cy,rad=100):
    A=arr(rows)
    best=(-1,0,0)
    H,W=canv.shape
    for dy in range(cy-rad,cy+rad+1):
        for dx in range(cx-rad,cx+rad+1):
            iy=dy-oy0; ix=dx-ox0
            if iy<0 or ix<0 or iy+64>H or ix+64>W: continue
            m=mask[iy:iy+64,ix:ix+64]
            n=int(m.sum())
            if n<700: continue
            same=int(((canv[iy:iy+64,ix:ix+64]==A)&m).sum())
            sc=same/n
            if sc>best[0]: best=(sc,dx,dy)
    return best

def build(level=None,attempt=None,verbose=False):
    fr=frames()
    # board produced by frame i belongs to the level/attempt reported by frame i+1's header
    import subprocess
    if level is None or attempt is None:
        st=subprocess.run(['./act','status'],capture_output=True,text=True).stdout
        import re as _re
        m=_re.search(r'level=(\d+) attempt=(\d+)',st)
        level=int(m.group(1)); attempt=int(m.group(2))
    for i,f in enumerate(fr):
        nxt=fr[i+1] if i+1<len(fr) else None
        f['blevel']=nxt['level'] if nxt else level
        f['battempt']=nxt['attempt'] if nxt else attempt
    idx=[i for i,f in enumerate(fr) if f['blevel']==level and f['battempt']==attempt]
    fl=fr[idx[0]:idx[-1]+1]
    cache={}
    if os.path.exists(CACHE): cache=json.load(open(CACHE))
    key=lambda f:'%d:%d:%d'%(level,f['attempt'],f['action'])
    off=(0,0); offs=[]; cells_w={}; nodes_w=set(); dirty=False; shut_ever=set(); hist=[]
    static={}; seen_multi={}
    for n,f in enumerate(fl):
        rows=f['rows']
        if n:
            k=key(f)
            if k in cache: off=tuple(cache[k])
            else:
                dx,dy,sc=rel_shift(prevrows,rows)
                cand=(off[0]-dx,off[1]-dy)
                if sc<0.85 and hist:
                    xs=[o[0] for _,o in hist]; ys=[o[1] for _,o in hist]
                    ox0,oy0=min(xs)-100,min(ys)-100
                    W=max(xs)+164-ox0; H=max(ys)+164-oy0
                    canv=np.zeros((H,W),dtype=np.uint8); msk=np.zeros((H,W),dtype=bool)
                    for rr,oo in hist:
                        canv[oo[1]-oy0:oo[1]-oy0+64, oo[0]-ox0:oo[0]-ox0+64]=arr(rr)
                        msk[oo[1]-oy0:oo[1]-oy0+64, oo[0]-ox0:oo[0]-ox0+64]=True
                    b=canvas_match(canv,msk,ox0,oy0,rows,cand[0],cand[1])
                    if b[0]>sc: cand=(b[1],b[2]); sc=b[0]
                off=cand; cache[k]=[off[0],off[1]]; dirty=True
                if verbose: print('  measure',f['action'],f['what'][:18],'off',off,round(sc,3))
        offs.append(off); prevrows=rows; hist.append((rows,off))
        if len(hist)>60: hist.pop(0)
        c,s=parse_frame(rows)
        for (x,y) in s: shut_ever.add((x+off[0],y+off[1]))
        for (x,y),v in c.items():
            k3=(x+off[0],y+off[1])
            if k3 in shut_ever: continue
            cells_w[k3]=v
        for (x,y) in track_nodes(rows): nodes_w.add((x+off[0],y+off[1]))
    if dirty: json.dump(cache,open(CACHE,'w'))
    cur=fl[-1]
    c,s=parse_frame(cur['rows'])
    cells={(x+off[0],y+off[1]):v for (x,y),v in c.items()}
    shut={(x+off[0],y+off[1]):v for (x,y),v in s.items()}
    for k2 in list(cells_w):
        if k2 in shut_ever: del cells_w[k2]
    for k2,v in cells.items():
        if k2 not in shut_ever: cells_w[k2]=v
    w_shut_ever=shut_ever
    return dict(off=off,cells=cells,shut=shut,world_cells=cells_w,nodes=nodes_w,frame=cur,offs=offs,fl=fl,level=level,shut_ever=w_shut_ever)

def w2s(w,p): return (p[0]-w['off'][0],p[1]-w['off'][1])
def s2w(w,p): return (p[0]+w['off'][0],p[1]+w['off'][1])

def show(w):
    cells=w['world_cells']; shut=w['shut']
    ph=sorted(cells)[0]
    nodes=set(n for n in w['nodes'] if n[0]%6==ph[0]%6 and n[1]%6==ph[1]%6)
    nodes-=set(cells)
    allp=set(cells)|set(shut)|nodes
    xs=sorted(set(p[0] for p in allp)); ys=sorted(set(p[1] for p in allp))
    print('world = screen +',w['off'],' (visible world x %d..%d y %d..%d)'%(w['off'][0],w['off'][0]+63,w['off'][1],w['off'][1]+63))
    print('     '+''.join('%-3d'%x for x in xs))
    for y in ys:
        line=''
        for x in xs:
            if (x,y) in shut: line+=('[S]' if shut[(x,y)]=='.' else '[X]')
            elif (x,y) in cells: line+=(' . ' if cells[(x,y)]=='.' else ' P ')
            elif (x,y) in nodes: line+=' ~ '
            else: line+='   '
        print('%3d  %s'%(y,line))
if __name__=='__main__':
    w=build(verbose=True); show(w)
    print('pegs visible',sum(1 for v in w['cells'].values() if v=='P'),'shuttles',w['shut'])
