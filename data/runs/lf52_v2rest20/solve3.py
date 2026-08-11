import sys, collections
sys.setrecursionlimit(10000)

CELLS={(1,1),(1,2),(1,3),(1,4),(2,1),(2,2),(2,3),(2,4),(3,3),(3,4),(4,1),(4,2),(4,3),(4,4),(5,1),(5,2),
 (1,8),(1,9),(2,8),(2,9),(3,8),(3,9),(4,8),
 (10,2),(11,1),(11,2),(11,3),(11,4),(11,5),(11,6),(11,7),(11,8),(11,9),
 (12,1),(12,2),(12,3),(12,4),(12,5),(12,6),(12,7),(12,8),(12,9),(13,3),(13,5),(13,7),(14,3),(14,5)}
ADJ=collections.defaultdict(set)
def link(a,b): ADJ[a].add(b); ADJ[b].add(a)
# region1 rows/cols
for a,b in [((1,1),(1,2)),((1,1),(2,1)),((1,2),(1,3)),((1,2),(2,2)),((1,3),(1,4)),((1,3),(2,3)),((1,4),(2,4)),
 ((2,1),(2,2)),((2,2),(2,3)),((2,3),(2,4)),((2,3),(3,3)),((2,4),(3,4)),((3,3),(3,4)),((3,3),(4,3)),((3,4),(4,4)),
 ((4,1),(4,2)),((4,1),(5,1)),((4,2),(4,3)),((4,2),(5,2)),((4,3),(4,4)),((5,1),(5,2)),
 ((1,8),(1,9)),((1,8),(2,8)),((1,9),(2,9)),((2,8),(2,9)),((2,8),(3,8)),((2,9),(3,9)),((3,8),(3,9)),((3,8),(4,8)),
 ((10,2),(11,2)),((11,1),(11,2)),((11,1),(12,1)),((11,2),(11,3)),((11,2),(12,2)),((11,3),(11,4)),((11,3),(12,3)),
 ((11,4),(11,5)),((11,4),(12,4)),((11,5),(11,6)),((11,5),(12,5)),((11,6),(11,7)),((11,6),(12,6)),
 ((11,7),(11,8)),((11,7),(12,7)),((11,8),(11,9)),((11,8),(12,8)),((11,9),(12,9)),
 ((12,1),(12,2)),((12,2),(12,3)),((12,3),(12,4)),((12,3),(13,3)),((12,4),(12,5)),((12,5),(12,6)),((12,5),(13,5)),
 ((12,6),(12,7)),((12,7),(12,8)),((12,7),(13,7)),((12,8),(12,9)),((13,3),(14,3)),((13,5),(14,5))]:
    link(a,b)
TRACK1=[(6,2),(7,2),(8,2),(9,2)]
TRACK2=[(5,8),(6,8),(7,8),(7,7),(7,6),(8,6),(9,6),(9,7),(9,8),(10,8)]
# docks: shuttle cell -> (neighbour cell, next cell beyond)
DOCK={(6,2):((5,2),(4,2)), (9,2):((10,2),(11,2)), (5,8):((4,8),(3,8)), (10,8):((11,8),(12,8))}
PEGS0=frozenset({(2,2),(5,2),(2,3),(4,3),(3,4),(2,8),(4,8),(10,2),(12,3),(13,3),(12,5),(13,5),(11,7),(12,8)})

DIRS=[(1,0),(-1,0),(0,1),(0,-1)]
def internal_jumps(pegs):
    out=[]
    for (c,r) in pegs:
        for dc,dr in DIRS:
            m=(c+dc,r+dr); l=(c+2*dc,r+2*dr)
            if m in pegs and l in CELLS and l not in pegs and m in ADJ[(c,r)] and l in ADJ[m]:
                out.append(('J',(c,r),m,l))
    return out
def dock_jumps(pegs,l1,l2):
    """export: peg jumps into empty docked shuttle; import: shuttle peg jumps out"""
    out=[]
    for sh,pos_list,load in ((1,TRACK1,l1),(2,TRACK2,l2)):
        for pos in pos_list:
            if pos not in DOCK: continue
            near,far=DOCK[pos]
            if load:   # import: shuttle peg over near -> far
                if near in pegs and far in CELLS and far not in pegs:
                    out.append(('I',sh,pos,near,far))
            else:      # export: peg at far jumps over near into shuttle
                if far in pegs and near in pegs:
                    out.append(('E',sh,pos,near,far))
    return out
def apply(pegs,l1,l2,mv):
    if mv[0]=='J':
        _,a,m,l=mv; return frozenset((pegs-{a,m})|{l}),l1,l2
    if mv[0]=='I':
        _,sh,pos,near,far=mv
        p=frozenset((pegs-{near})|{far})
        return p,(False if sh==1 else l1),(False if sh==2 else l2)
    _,sh,pos,near,far=mv
    p=frozenset(pegs-{near,far})
    return p,(True if sh==1 else l1),(True if sh==2 else l2)

def solve(pegs,l1,l2,limit):
    dead=set()
    path=[]
    def dfs(pegs,l1,l2,depth):
        tot=len(pegs)+l1+l2
        if tot==1: return True
        if depth==0: return False
        key=(pegs,l1,l2)
        if key in dead: return False
        mvs=internal_jumps(pegs)+dock_jumps(pegs,l1,l2)
        for mv in mvs:
            np,nl1,nl2=apply(pegs,l1,l2,mv)
            path.append(mv)
            if dfs(np,nl1,nl2,depth-1): return True
            path.pop()
        dead.add(key)
        return False
    ok=dfs(pegs,l1,l2,limit)
    return path if ok else None

if __name__=='__main__':
    sol=solve(PEGS0,False,False,13)
    if sol:
        print('SOLUTION',len(sol),'jumps')
        for m in sol: print('  ',m)
    else: print('no solution in 13')
