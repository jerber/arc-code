import re
CELLCH=set('12e3')
def last_board(path='logs.txt'):
    txt=open(path).read()
    i=txt.rfind('[final]')
    j=txt.rfind('[anim')
    if i<0 or (j>i): i=j
    lines=txt[i:].split('\n')[1:]
    rows=[l for l in lines if re.fullmatch(r'[0-9a-f]{64}',l)][:64]
    return rows
def find_cells(rows):
    cells={}
    for y in range(1,60):
        for x in range(1,60):
            blk=[rows[y+dy][x:x+4] for dy in range(4)]
            if not all(ch in CELLCH for r in blk for ch in r): continue
            # ring must not be cell-content chars mostly: require left col x-1 and top row not cell chars
            ring=[rows[y-1][x-1+i] for i in range(6)]+[rows[y+4][x-1+i] for i in range(6)]
            ring+=[rows[y+dy][x-1] for dy in range(4)]+[rows[y+dy][x+4] for dy in range(4)]
            if any(ch in set('12e') for ch in ring): continue
            cells[(x,y)]=blk
    return cells
def classify(blk):
    s=set(''.join(blk))
    if 'e' in s: return 'P'   # peg
    if '2' in s: return 'g'   # ghost dest
    if s<= set('13'): return '.' if '3' not in s else '.'
    return '?'
def logical(rows=None):
    if rows is None: rows=last_board()
    cells=find_cells(rows)
    xs=sorted(set(x for x,y in cells)); ys=sorted(set(y for x,y in cells))
    return cells,xs,ys
def show(rows=None):
    if rows is None: rows=last_board()
    cells,xs,ys=logical(rows)
    print('cell x origins:',xs)
    print('cell y origins:',ys)
    for y in ys:
        line=[]
        for x in xs:
            b=cells.get((x,y))
            line.append(classify(b) if b else ' ')
        print('y=%2d '%y+''.join(line))
    # selected marker
    sel=[(x,y) for (x,y),b in cells.items() if '3' in ''.join(b)]
    if sel: print('selected-ish:',sel)
if __name__=='__main__':
    show()

def shuttle(rows=None):
    if rows is None: rows=last_board()
    pts=[(x,y) for y in range(64) for x in range(64) if rows[y][x]=='c']
    if not pts: return None
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    return (min(xs),max(xs),min(ys),max(ys))
