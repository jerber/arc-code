"""Generic peg-solitaire board reader for lf52."""
from parse import load_states

def read_board(g):
    """Return (cells dict (i,j)->'.'/'P', geom) from a grid."""
    # tiles are 4x4 blocks of '1' (or containing 'e'/'2'/'3'); find candidate origins
    # detect pitch by scanning row/col of interior
    # Approach: find all cells that are '1' or 'e'; cluster into 4x4 blocks.
    on=[(x,y) for y in range(64) for x in range(64) if g[y][x] in '1e2']
    if not on: return None,None
    xs=sorted({x for x,y in on}); ys=sorted({y for x,y in on})
    def origins(vals):
        # vals sorted; groups of 4 consecutive
        grps=[];cur=[vals[0]]
        for v in vals[1:]:
            if v==cur[-1]+1: cur.append(v)
            else: grps.append(cur); cur=[v]
        grps.append(cur)
        return [gp[0] for gp in grps], grps
    ox,gx=origins(xs); oy,gy=origins(ys)
    cells={}
    for j,y in enumerate(oy):
        for i,x in enumerate(ox):
            blk=[g[y+dy][x+dx] for dy in range(len(gy[j])) for dx in range(len(gx[i]))]
            s=set(blk)
            if s<= set('a95'): continue
            if 'e' in s: cells[(i,j)]='P'
            elif '1' in s or '2' in s or '3' in s: cells[(i,j)]='.'
    geom=(ox,oy,[len(a) for a in gx],[len(a) for a in gy])
    return cells,geom

def show(cells):
    if not cells: return '(empty)'
    W=max(i for i,j in cells)+1; H=max(j for i,j in cells)+1
    return '\n'.join(''.join(cells.get((i,j),' ') for i in range(W)) for j in range(H))

def center(geom,i,j):
    ox,oy,wx,wy=geom
    return ox[i]+wx[i]//2, oy[j]+wy[j]//2

if __name__=='__main__':
    S=load_states()
    c,geom=read_board(S[-1][2])
    print(S[-1][0])
    print(show(c))
    print('geom ox',geom[0]); print('geom oy',geom[1])
    print('wx',geom[2],'wy',geom[3])
    print('pegs',sorted(k for k,v in c.items() if v=='P'))
