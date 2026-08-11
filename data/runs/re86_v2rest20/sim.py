#!/usr/bin/env python3
"""Simulator for multi-part shapes: movement, obstacle blocking, swatch recolouring."""
import parse, deform

D={'ACTION1':(0,-3),'ACTION2':(0,3),'ACTION3':(-3,0),'ACTION4':(3,0)}

def board(idx=-1):
    bl=parse.load(); return bl[idx][1][-1][1]

def obstacles(g, col='1'):
    return {(x,y) for y in range(63) for x in range(64) if g[y][x]==col}

def swatch_blocks(g):
    """NxN colour blocks framed by '2' -> list (colour, cells)."""
    out=[]; seen=set()
    for y in range(63):
        for x in range(64):
            c=g[y][x]
            if c in ('5','4','2','0') or (x,y) in seen: continue
            st=[(x,y)]; comp={(x,y)}; seen.add((x,y))
            while st:
                cx,cy=st.pop()
                for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=cx+dx,cy+dy
                    if 0<=nx<64 and 0<=ny<63 and (nx,ny) not in comp and g[ny][nx]==c:
                        comp.add((nx,ny)); seen.add((nx,ny)); st.append((nx,ny))
            xs=[p[0] for p in comp]; ys=[p[1] for p in comp]
            w=max(xs)-min(xs)+1; h=max(ys)-min(ys)+1
            if len(comp)==w*h and w==h and w>=3:
                ring=all(g[b][a]=='2' for a in range(min(xs)-1,max(xs)+2) for b in (min(ys)-1,max(ys)+1)
                         if 0<=a<64 and 0<=b<63)
                if ring: out.append((c,comp))
    return out

def cells(parts,state):
    u=set()
    for (k,r),c in zip(parts,state): u|=deform.cells_of(k,c,r)
    return u

def simulate(parts, state, colour, actions, obst, sw, trace=False):
    for a in actions:
        d=D[a]
        state=deform.step(parts,state,d,obst)
        cs={p for p in cells(parts,state) if 0<=p[0]<64 and 0<=p[1]<63}
        for c,block in sw:
            if cs & block: colour=c
        if trace: print("   ",a,state,colour)
    return state, colour
