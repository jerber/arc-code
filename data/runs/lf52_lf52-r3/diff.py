import re,sys
def all_boards(path='logs.txt'):
    txt=open(path).read()
    blocks=[]
    # split on action headers
    parts=re.split(r'\n(?=={10,})',txt)
    for p in parts:
        m=re.search(r'action (\d+) \| level (\d+) attempt (\d+) \| score (\d+) \| (.*?)(?:\n|$)',p)
        if not m: continue
        i=p.rfind('[final]')
        if i<0: i=p.rfind('[anim')
        lines=p[i:].split('\n')[1:]
        rows=[l for l in lines if re.fullmatch(r'[0-9a-f]{64}',l)][:64]
        if len(rows)==64: blocks.append((m.group(1),m.group(2),m.group(4),m.group(5),rows))
    return blocks
if __name__=='__main__':
    b=all_boards()
    n=int(sys.argv[1]) if len(sys.argv)>1 else 2
    sel=b[-n:]
    for k in range(1,len(sel)):
        a,c=sel[k-1],sel[k]
        print('--- action',a[0],a[3],'->',c[0],c[3],'level',c[1],'score',c[2])
        d=[]
        for y in range(64):
            for x in range(64):
                if a[4][y][x]!=c[4][y][x]: d.append((x,y,a[4][y][x],c[4][y][x]))
        print('changed',len(d))
        # summarize by bounding box per color transition
        from collections import defaultdict
        m=defaultdict(list)
        for x,y,o,nn in d: m[(o,nn)].append((x,y))
        for k2,v in sorted(m.items()):
            xs=[p[0] for p in v]; ys=[p[1] for p in v]
            print('  %s->%s n=%d x[%d..%d] y[%d..%d]'%(k2[0],k2[1],len(v),min(xs),max(xs),min(ys),max(ys)))
