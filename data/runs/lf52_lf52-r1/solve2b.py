import itertools,sys
def build(variant):
    cells=[]
    for j in range(3):
        for i in range(7): cells.append(('A',i,j))
    if variant!='nolink_noO': cells.append(('O',0,0))
    for j in range(2):
        for i in range(2): cells.append(('B',i,j))
    idx={c:k for k,c in enumerate(cells)}
    triples=[]
    def add(a,b,c):
        if a in idx and b in idx and c in idx: triples.append((idx[a],idx[b],idx[c]))
    for j in range(3):
        for i in range(7):
            add(('A',i,j),('A',i+1,j),('A',i+2,j)); add(('A',i,j),('A',i-1,j),('A',i-2,j))
            add(('A',i,j),('A',i,j+1),('A',i,j+2)); add(('A',i,j),('A',i,j-1),('A',i,j-2))
    for j in range(2):
        for i in range(2):
            add(('B',i,j),('B',i+1,j),('B',i+2,j)); add(('B',i,j),('B',i-1,j),('B',i-2,j))
            add(('B',i,j),('B',i,j+1),('B',i,j+2)); add(('B',i,j),('B',i,j-1),('B',i,j-2))
    if variant=='nolink_noO':
        chain=[('A',3,1),('A',4,1),('A',5,1),('A',6,1),('B',0,1),('B',1,1)]
    else:
        chain=[('A',4,1),('A',5,1),('A',6,1),('O',0,0),('B',0,1),('B',1,1)]
    for k in range(len(chain)-2):
        add(chain[k],chain[k+1],chain[k+2]); add(chain[k+2],chain[k+1],chain[k])
    return cells,idx,list(set(triples))

def solve(variant, opeg):
    cells,idx,triples=build(variant)
    st=0
    base=[('A',1,1),('A',2,1),('A',4,1),('A',6,1),('B',0,1)]
    if opeg and ('O',0,0) in idx: base.append(('O',0,0))
    for c in base: st|=1<<idx[c]
    seen=set()
    def dfs(state,path):
        if bin(state).count('1')==1: return path
        if state in seen: return None
        seen.add(state)
        for a,b,c in triples:
            if state>>a&1 and state>>b&1 and not (state>>c&1):
                ns=state & ~(1<<a) & ~(1<<b) | (1<<c)
                r=dfs(ns,path+[(cells[a],cells[c])])
                if r: return r
        return None
    return dfs(st,[])

for v in ['link','nolink_noO']:
    for op in ([True,False] if v=='link' else [False]):
        r=solve(v,op)
        print(v,'orangepeg' if op else 'orangeempty', '->', 'SOLVED' if r else 'none')
        if r:
            for m in r: print('   ',m)
