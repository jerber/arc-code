from board import Board,grid
BIG=[(1,1),(2,1),(4,1),(5,1),(1,2),(2,2),(4,2),(5,2),(1,3),(2,3),(3,3),(4,3),(1,4),(2,4),(3,4),(4,4)]
P4=[(1,8),(2,8),(3,8),(4,8),(1,9),(2,9),(3,9)]
R=[(10,2)]+[(x,y) for y in range(1,10) for x in (11,12)]+[(13,3),(14,3),(13,5),(14,5),(13,7)]
T1=[(6,2),(7,2),(8,2),(9,2)]
T2=[(5,8),(6,8),(7,8),(7,7),(7,6),(8,6),(9,6),(9,7),(9,8),(10,8)]
CELLS=set(BIG)|set(P4)|set(R)
TRACK=set(T1)|set(T2)
ALL=CELLS|TRACK

def locate(b):
    best=None
    seen={k for k in b.cells}|set(b.track)
    for dx in range(-8,9):
        for dy in range(-6,7):
            sc=0
            for (X,Y) in seen:
                sc += 1 if (X+dx,Y+dy) in ALL else -3
            if best is None or sc>best[0]: best=(sc,dx,dy)
    return best[1],best[2]

def pix(b,dx,dy,w):
    X,Y=w[0]-dx,w[1]-dy
    return b.ox+6*X+1, b.oy+6*Y+1

def state(path='/tmp/cur.txt'):
    b=Board(grid(path)); dx,dy=locate(b)
    pegs=sorted((k[0]+dx,k[1]+dy) for k,v in b.cells.items() if v=='PEG')
    sh=sorted((k[0]+dx,k[1]+dy) for k,v in b.cells.items() if v in ('SHUTTLE','SPEG'))
    shp=sorted((k[0]+dx,k[1]+dy) for k,v in b.cells.items() if v=='SPEG')
    return b,dx,dy,pegs,sh,shp
