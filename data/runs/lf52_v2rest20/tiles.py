import parse,collections,sys
def grid(rows): return [[int(c,16) for c in r] for r in rows]
def tiles(g):
    """find 4x4 tiles: cells with value in {1,e} grouped"""
    seen=set(); out=[]
    for y in range(64):
        for x in range(64):
            if g[y][x] in (1,0xe) and (x,y) not in seen:
                # flood fill 8-conn over {1,e}
                st=[(x,y)];comp=[]
                seen.add((x,y))
                while st:
                    cx,cy=st.pop();comp.append((cx,cy))
                    for dx in(-1,0,1):
                        for dy in(-1,0,1):
                            nx,ny=cx+dx,cy+dy
                            if 0<=nx<64 and 0<=ny<64 and (nx,ny) not in seen and g[ny][nx] in (1,0xe):
                                seen.add((nx,ny));st.append((nx,ny))
                xs=[p[0] for p in comp];ys=[p[1] for p in comp]
                pat=''.join(''.join('%x'%g[yy][xx] for xx in range(min(xs),max(xs)+1)) for yy in range(min(ys),max(ys)+1))
                out.append((min(xs),min(ys),max(xs),max(ys),len(comp),pat))
    return out
if __name__=='__main__':
    hdr,rows=parse.last()
    g=grid(rows)
    ts=tiles(g)
    print(hdr,'ntiles',len(ts))
    for t in ts: print(t)
