import parse,collections,sys

def best_shift(a,b,maxs=40):
    """find (dx,dy) so that b[y][x] == a[y+dy][x+dx] for most non-'a' pixels"""
    best=None
    for dy in range(-maxs,maxs+1):
        for dx in range(-maxs,maxs+1):
            same=0; diff=0
            for y in range(1,64,1):
                ay=y+dy
                if not(1<=ay<64): continue
                ra=a[ay]; rb=b[y]
                for x in range(0,64,1):
                    ax=x+dx
                    if not(0<=ax<64): continue
                    if ra[ax]=='a' and rb[x]=='a': continue
                    if ra[ax]==rb[x]: same+=1
                    else: diff+=1
            if same+diff<200: continue
            score=same-3*diff
            if best is None or score>best[0]: best=(score,dx,dy,same,diff)
    return best
if __name__=='__main__':
    bs=parse.blocks()
    i,j=int(sys.argv[1]),int(sys.argv[2])
    print(best_shift(bs[i][1],bs[j][1]))
