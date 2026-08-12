"""Level-6 simulator: cells, track, pivots, shuttles, camera."""
CELLS=set()
for c in range(2,6):
    for r in range(2,6): CELLS.add((c,r))
for c in range(2,8):
    for r in range(6,9): CELLS.add((c,r))
CELLS.add((4,9))
for c in range(15,19): CELLS.add((c,2))
for c in range(15,26): CELLS.add((c,3))
CELLS|={(16,4),(17,4)}
CELLS|={(27,3),(27,4),(27,5)}
CELLS|={(23,5),(23,6),(23,7),(22,7),(21,7),(21,8),(21,9),(25,5)}
PIVOTS={(15,4),(18,4),(24,4)}
TRACK=set()
for c in range(8,19): TRACK.add((c,7))
TRACK|={(15,5),(15,6),(18,5),(18,6)}
TRACK|={(24,5),(24,6),(24,7),(25,7),(26,7),(26,6),(26,5),(26,4),(26,3)}
DIRS={'ACTION1':(0,-1),'ACTION2':(0,1),'ACTION3':(-1,0),'ACTION4':(1,0)}
CAMMAX=104
class St:
    def __init__(s,pegs,shuttles,cam):
        s.pegs=dict(pegs); s.sh=[list(x) for x in shuttles]; s.cam=cam; s.log=[]
    def clone(s):
        return St(s.pegs,[tuple(x) for x in s.sh],s.cam)
    def at(s,cell):
        """what occupies cell: ('peg',v) ('shuttle',i)"""
        if cell in s.pegs: return ('peg',s.pegs[cell])
        for i,(p,c) in enumerate(s.sh):
            if p==cell: return ('sh',i)
        return None
    def occupant(s,cell):
        """piece value at cell or None"""
        o=s.at(cell)
        if o is None: return None
        if o[0]=='peg': return o[1]
        return s.sh[o[1]][1]
    def visible(s,cell):
        x0=6*cell[0]-s.cam
        return -3<=x0<=63 and x0+3>=0
    def press(s,act):
        d=DIRS[act]
        moved={}
        for _ in range(4):
            for i,(p,c) in enumerate(s.sh):
                if i in moved: continue
                t=(p[0]+d[0],p[1]+d[1])
                if t in TRACK and all(o[0]!=t for o in s.sh):
                    s.sh[i][0]=t; moved[i]=d[0]
        dx=0
        for i,dd in moved.items():
            if s.sh[i][1]=='G': dx=dd*6
        s.cam=max(0,min(CAMMAX,s.cam+dx))
        s.log.append((act,'cam=%d'%s.cam,'sh=%s'%[tuple(x) for x in s.sh]))
        return s
    def jump(s,a,b,c):
        assert s.visible(a),'select %s not visible cam=%d'%(a,s.cam)
        assert s.visible(c),'land %s not visible cam=%d'%(c,s.cam)
        av=s.occupant(a); assert av in ('G','R'),'no piece at %s'%(a,)
        # collinear consecutive
        assert (b[0]-a[0],b[1]-a[1])==(c[0]-b[0],c[1]-b[1]) and abs(b[0]-a[0])+abs(b[1]-a[1])==1,'not a jump %s %s %s'%(a,b,c)
        bo=s.at(b)
        if b in PIVOTS: bv='P'
        else:
            bv=s.occupant(b); assert bv in ('G','R'),'nothing to jump over at %s'%(b,)
        co=s.at(c)
        assert (c in CELLS and co is None) or (co and co[0]=='sh' and s.sh[co[1]][1] is None),'landing %s blocked/invalid'%(c,)
        # remove from a
        ao=s.at(a)
        if ao[0]=='peg': del s.pegs[a]
        else: s.sh[ao[1]][1]=None
        # consume?
        if bv=='G' and av=='G':
            bo2=s.at(b)
            if bo2[0]=='peg': del s.pegs[b]
            else: s.sh[bo2[1]][1]=None
        # place at c
        if co and co[0]=='sh': s.sh[co[1]][1]=av
        else: s.pegs[c]=av
        s.log.append(('JUMP %s->%s over %s'%(a,c,b),'cam=%d'%s.cam,'greens=%d'%s.greens()))
        return s
    def greens(s):
        return sum(1 for v in s.pegs.values() if v=='G')+sum(1 for p,c in s.sh if c=='G')
    def show(s):
        print('cam',s.cam,'pegs',sorted(s.pegs.items()),'sh',[tuple(x) for x in s.sh],'greens',s.greens())

from collections import deque
def bfs_press(state, want, maxd=30):
    """find press sequence so shuttle positions match `want` (dict idx->pos) and
       optionally cam target want.get('cam'). Returns list of actions or None."""
    camt=want.get('cam')
    start=(tuple(p for p,c in state.sh), state.cam)
    cargo=[c for p,c in state.sh]
    blocked=set(state.pegs)
    def ok(st):
        pos,cam=st
        for k,v in want.items():
            if k=='cam': continue
            if pos[k]!=v: return False
        return camt is None or cam==camt
    if ok(start): return []
    seen={start}; q=deque([(start,[])])
    while q:
        (pos,cam),path=q.popleft()
        if len(path)>=maxd: continue
        for act,d in DIRS.items():
            p=list(pos); moved={}
            for _ in range(4):
                for i in range(len(p)):
                    if i in moved: continue
                    t=(p[i][0]+d[0],p[i][1]+d[1])
                    if t in TRACK and t not in p:
                        p[i]=t; moved[i]=d[0]
            if not moved: continue
            dx=0
            for i,dd in moved.items():
                if cargo[i]=='G': dx=dd*6
            nc=max(0,min(CAMMAX,cam+dx))
            st=(tuple(p),nc)
            if st in seen: continue
            seen.add(st); np=path+[act]
            if ok(st): return np
            q.append((st,np))
    return None
