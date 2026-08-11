import re
HOLE=set('123e')
def last_board(path='logs.txt'):
    txt=open(path).read()
    i=txt.rfind('[final]'); j=txt.rfind('[anim')
    if j>i: i=j
    lines=txt[i:].split('\n')[1:]
    return [l for l in lines if re.fullmatch(r'[0-9a-f]{64}',l)][:64]

def parse(rows):
    cells={}; shut={}
    for y in range(1,60):
        for x in range(1,60):
            blk=''.join(rows[y+dy][x:x+4] for dy in range(4))
            ring=[rows[y-1][x-1+i] for i in range(6)]+[rows[y+4][x-1+i] for i in range(6)]
            ring+=[rows[y+dy][x-1] for dy in range(4)]+[rows[y+dy][x+4] for dy in range(4)]
            if all(ch in HOLE for ch in blk) and not any(ch in set('12e') for ch in ring):
                cells[(x,y)]='P' if 'e' in blk else '.'
            elif all(ch in set('ce') for ch in blk) and 'c' in blk and all(ch=='b' for ch in ring):
                shut[(x,y)]='P' if 'e' in blk else '.'
    return cells,shut

def lattice(cells,shut):
    pts=list(cells)+list(shut)
    ox=pts[0][0]%6; oy=pts[0][1]%6
    return ox,oy

def track_h(rows,x,y):
    return all(rows[y+1][xx]=='5' and rows[y+2][xx]=='5' for xx in range(x,x+4))
def track_v(rows,x,y):
    return all(rows[yy][x+1]=='5' and rows[yy][x+2]=='5' for yy in range(y,y+4))

def nodes(rows,cells,shut):
    ox,oy=lattice(cells,shut)
    ns=set(shut)
    for y in range(oy,60,6):
        for x in range(ox,60,6):
            if (x,y) in cells: continue
            if track_h(rows,x,y) or track_v(rows,x,y): ns.add((x,y))
    return ns

def report():
    rows=last_board()
    cells,shut=parse(rows)
    ns=nodes(rows,cells,shut)
    ox,oy=lattice(cells,shut)
    allp=set(cells)|set(shut)|ns
    xs=sorted(set(p[0] for p in allp)); ys=sorted(set(p[1] for p in allp))
    print('lattice offset',ox,oy)
    print('     '+''.join('%-3d'%x for x in xs))
    for y in ys:
        line=''
        for x in xs:
            if (x,y) in shut: line+=('[S]' if shut[(x,y)]=='.' else '[X]')
            elif (x,y) in cells: line+=(' . ' if cells[(x,y)]=='.' else ' P ')
            elif (x,y) in ns: line+=' ~ '
            else: line+='   '
        print('%3d  %s'%(y,line))
    print('cells',len(cells),'pegs',sum(1 for v in cells.values() if v=='P'),'shuttles',shut)
if __name__=='__main__': report()
