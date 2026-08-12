"""BFS over joint shuttle positions to bring shuttle i to a target track cell."""
import planner as P, collections
def route(pos,i,target,maxd=40):
    start=tuple(pos); seen={start:None}; q=collections.deque([start])
    while q:
        st=q.popleft()
        if st[i]==target:
            seq=[]; cur=st
            while seen[cur]: prev,mv=seen[cur]; seq.append(mv); cur=prev
            return list(reversed(seq))
        for name,d in P.DIRS.items():
            ns=P.moves_of_shuttles(st,d)
            if ns!=st and ns not in seen:
                seen[ns]=(st,name); q.append(ns)
    return None
