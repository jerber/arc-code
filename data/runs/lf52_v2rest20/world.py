"""Merge multiple scrolled views into one world map, in world pixel coords."""
import parse, level, collections, sys, json, os

W=200; H=120   # world canvas (world x offset 40 => canvas col x+40)
OFF=40
def blank(): return [['?']*W for _ in range(H)]

def paste(canvas, rows, ox, oy):
    for y in range(64):
        for x in range(64):
            cx,cy=x+ox+OFF, y+oy+OFF
            if 0<=cx<W and 0<=cy<H:
                canvas[cy][cx]=rows[y][x]

def score(canvas, rows, ox, oy):
    same=diff=0
    for y in range(1,64):
        for x in range(64):
            cx,cy=x+ox+OFF,y+oy+OFF
            if not(0<=cx<W and 0<=cy<H): continue
            c=canvas[cy][cx]
            if c=='?': continue
            if c=='a' and rows[y][x]=='a': continue
            if c==rows[y][x]: same+=1
            else: diff+=1
    return same,diff

def fit(canvas, rows, rng=60):
    best=None
    for oy in (0,):
        for ox in range(-rng,rng+1):
            s,d=score(canvas,rows,ox,oy)
            if s+d<300: continue
            sc=s-4*d
            if best is None or sc>best[0]: best=(sc,ox,oy,s,d)
    return best

if __name__=='__main__':
    idxs=[int(a) for a in sys.argv[1:]]
    bs=parse.blocks()
    canvas=blank()
    paste(canvas,bs[idxs[0]][1],0,0)
    offs={idxs[0]:(0,0)}
    for i in idxs[1:]:
        b=fit(canvas,bs[i][1])
        print('view',i,'fit',b)
        if b and b[3]>b[4]:
            paste(canvas,bs[i][1],b[1],b[2]); offs[i]=(b[1],b[2])
    json.dump(offs,open('offsets.json','w'))
    # report extent
    xs=[x for y in range(H) for x in range(W) if canvas[y][x]!='?']
    ys=[y for y in range(H) for x in range(W) if canvas[y][x]!='?']
    print('known world pixels x %d..%d y %d..%d (world coords = canvas-%d)'%(min(xs)-OFF,max(xs)-OFF,min(ys)-OFF,max(ys)-OFF,0))
    open('worldmap.txt','w').write('\n'.join(''.join(r) for r in canvas))
