#!/usr/bin/env python3
"""Extract coarse (block) grid from a fine 64x64 board.
Blocks are 5x5. Origin at x=9,y=9 for level 1; derive generally."""
import parse

def coarse(g, ox=9, oy=9, nx=9, ny=10, w=5):
    out=[]
    for by in range(ny):
        row=[]
        for bx in range(nx):
            cells=[g[oy+by*w+dy][ox+bx*w+dx] for dy in range(w) for dx in range(w)]
            from collections import Counter
            row.append(Counter(cells).most_common(1)[0][0])
        out.append(row)
    return out

if __name__=="__main__":
    e=parse.load()
    for h,g in e:
        print(h)
        c=coarse(g)
        for r in c: print(''.join(r))
