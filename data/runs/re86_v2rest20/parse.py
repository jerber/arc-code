#!/usr/bin/env python3
"""Parse logs.txt into board states."""
import re, sys, collections

def load(path="logs.txt"):
    """Return list of (header, plan, boards[list of grid]) blocks. Only [final]/[board] kept."""
    txt = open(path).read()
    blocks = txt.split("="*80)
    out=[]
    for b in blocks[1:]:
        lines=b.strip("\n").split("\n")
        header=lines[0]
        # find all grid segments: contiguous lines of 64 hex chars
        grids=[]; cur=[]
        tags=[]; curtag=None
        pending=None
        for ln in lines[1:]:
            if re.fullmatch(r"[0-9a-f]{64}", ln):
                cur.append(ln)
            else:
                if cur:
                    grids.append((curtag,cur)); cur=[]
                m=re.match(r"\[(\w+)", ln.strip())
                if m: curtag=m.group(1)
        if cur: grids.append((curtag,cur))
        out.append((header, grids))
    return out

def final_grid(path="logs.txt", idx=-1):
    blocks=load(path)
    h,grids=blocks[idx]
    return h, grids[-1][1]

def objects(grid, bg='5'):
    """connected components (4-conn) of non-bg cells, grouped"""
    H=len(grid); W=len(grid[0])
    seen=[[False]*W for _ in range(H)]
    comps=[]
    for y in range(H):
        for x in range(W):
            if grid[y][x]!=bg and not seen[y][x]:
                st=[(x,y)]; seen[y][x]=True; cells=[]
                while st:
                    cx,cy=st.pop(); cells.append((cx,cy))
                    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                        nx,ny=cx+dx,cy+dy
                        if 0<=nx<W and 0<=ny<H and not seen[ny][nx] and grid[ny][nx]!=bg:
                            seen[ny][nx]=True; st.append((nx,ny))
                comps.append(cells)
    return comps

def describe(grid):
    for cells in objects(grid):
        xs=[c[0] for c in cells]; ys=[c[1] for c in cells]
        cnt=collections.Counter(grid[y][x] for x,y in cells)
        print(f"n={len(cells):4d} bbox=({min(xs)},{min(ys)})-({max(xs)},{max(ys)}) colors={dict(cnt)}")

def diff(g1,g2):
    d=[]
    for y in range(len(g1)):
        for x in range(len(g1[0])):
            if g1[y][x]!=g2[y][x]: d.append((x,y,g1[y][x],g2[y][x]))
    return d

if __name__=="__main__":
    h,g=final_grid()
    print(h)
    describe(g)
