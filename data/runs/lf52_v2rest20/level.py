"""Parse a board into: lattice cells (peg/empty), walls, pipe-track cells, shuttles."""
import parse, collections

PEG=0xe; EMPTY=1; GHOST=2; WALL=5; ORANGE=0xc; FRAME=0xb; INTER=0

def grid(rows): return [[int(c,16) for c in r] for r in rows]

def find_tiles(g):
    """4x4 blocks whose 16 px are in tilevals; returns dict (x0,y0)->kind"""
    out={}
    for y in range(61):
        for x in range(61):
            vals=[g[y+j][x+i] for j in range(4) for i in range(4)]
            s=set(vals)
            if s<= {1,PEG,GHOST} and vals[0] in (1,GHOST):   # panel tile
                out[(x,y)]='peg' if PEG in s else ('ghost' if GHOST in s else 'empty')
            elif s<={ORANGE,PEG}:      # shuttle interior
                out[(x,y)]='shuttle_peg' if PEG in s else 'shuttle_empty'
    return out

def dedupe(tiles):
    """tile detector may match overlapping windows; keep those on a consistent lattice"""
    xs=collections.Counter(x%6 for x,y in tiles); ys=collections.Counter(y%6 for x,y in tiles)
    mx=xs.most_common(1)[0][0]; my=ys.most_common(1)[0][0]
    return {k:v for k,v in tiles.items() if k[0]%6==mx and k[1]%6==my}, mx, my

def parse_board(rows):
    g=grid(rows)
    tiles,mx,my=dedupe(find_tiles(g))
    cells={}; shuttles={}
    for (x,y),k in tiles.items():
        c,r=(x-mx)//6,(y-my)//6
        if k.startswith('shuttle'): shuttles[(c,r)] = (k=='shuttle_peg')
        else: cells[(c,r)] = (k=='peg')
    # walls between lattice-adjacent panel cells
    def px(c,r): return (mx+6*c, my+6*r)
    conn=set()
    for (c,r) in cells:
        for dc,dr in((1,0),(0,1)):
            n=(c+dc,r+dr)
            if n not in cells: continue
            x0,y0=px(c,r)
            if dc: gap=[g[y0+j][x0+4+i] for j in range(4) for i in range(2)]
            else:  gap=[g[y0+4+j][x0+i] for j in range(2) for i in range(4)]
            if WALL not in gap: conn.add(((c,r),n)); conn.add((n,(c,r)))
    # track cells: central 2x2 all WALL, and not a panel cell
    track=set()
    C=(64-mx)//6+1; R=(64-my)//6+1
    for c in range(-1,C+1):
        for r in range(-1,R+1):
            if (c,r) in cells: continue
            x0,y0=px(c,r)
            if x0+3>63 or y0+3>63 or x0<0 or y0<0: continue
            if all(g[y0+j][x0+i]==WALL for j in (1,2) for i in (1,2)): track.add((c,r))
    for s in shuttles: track.add(s)
    # track adjacency
    tconn=set()
    for (c,r) in track:
        for dc,dr in((1,0),(0,1)):
            n=(c+dc,r+dr)
            if n not in track: continue
            x0,y0=px(c,r)
            if dc: gap=[g[y0+j][x0+4+i] for j in (1,2) for i in range(2)]
            else:  gap=[g[y0+4+j][x0+i] for j in range(2) for i in (1,2)]
            if all(v==WALL for v in gap): tconn.add(((c,r),n)); tconn.add((n,(c,r)))
    return dict(origin=(mx,my),cells=cells,shuttles=shuttles,conn=conn,track=track,tconn=tconn)

def show(L):
    cells=L['cells']; sh=L['shuttles']; tr=L['track']
    allk=set(cells)|set(sh)|tr
    cs=[k[0] for k in allk]; rs=[k[1] for k in allk]
    print('cols %d..%d rows %d..%d  pegs=%d cells=%d shuttles=%s'%(min(cs),max(cs),min(rs),max(rs),
        sum(cells.values())+sum(sh.values()),len(cells),sh))
    hdr='    '+''.join(str(c%10) for c in range(min(cs),max(cs)+1))
    print(hdr)
    for r in range(min(rs),max(rs)+1):
        line=''
        for c in range(min(cs),max(cs)+1):
            k=(c,r)
            if k in sh: line+= 'S' if sh[k] else 's'
            elif k in cells: line+= 'O' if cells[k] else '.'
            elif k in tr: line+='+'
            else: line+=' '
        print('%3d %s'%(r,line))

if __name__=='__main__':
    h,rows=parse.last(); print(h)
    L=parse_board(rows); show(L)
    print('cell-conns:',len(L['conn'])//2,'track-conns:',len(L['tconn'])//2)
