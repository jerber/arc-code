import re,sys
def boards(path='logs.txt'):
    txt=open(path).read()
    return txt
def last_board(path='logs.txt'):
    txt=open(path).read()
    idx=max(txt.rfind('[final]'),txt.rfind('[anim'))
    # take from last marker
    i=txt.rfind('[final]')
    if i<0: i=txt.rfind('[anim')
    lines=txt[i:].split('\n')[1:]
    rows=[l for l in lines if re.fullmatch(r'[0-9a-f]{64}',l)][:64]
    return rows
def cells(rows):
    g={}
    for r in range(7):
        for c in range(7):
            y=12+6*r; x=11+6*c
            if y+3>63 or x+3>63: continue
            blk=[rows[y+dy][x:x+4] for dy in range(4)]
            vals=set(''.join(blk))
            if all(ch=='a' for ch in ''.join(blk)): continue
            g[(r,c)]=blk
    return g
if __name__=='__main__':
    rows=last_board()
    g=cells(rows)
    for r in range(7):
        line=[]
        for c in range(7):
            b=g.get((r,c))
            if b is None: line.append(' . ')
            else:
                s=set(''.join(b))
                line.append(('['+''.join(sorted(s))+']').ljust(5))
        print(r,' '.join(line))
