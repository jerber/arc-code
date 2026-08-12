import sys, game, patrol
hdr,g=game.load()
print(hdr)
B=game.Board(g); B.dump()
E=B.entities(); print(E)
goal=None
if len(sys.argv)>1:
    goal=tuple(int(x) for x in sys.argv[1].split(','))
L=patrol.Lv(g,goal=goal)
print('start',L.start,'goal',L.goal,'nodes',len(L.nodes))
print('patrols',L.patrols); print('statics',L.statics)
r=patrol.search(L,T=90)
if not r:
    print('NO PLAN'); sys.exit(1)
print('plan',''.join(r),len(r))
trs=[patrol.traj(L,p,d,len(r)+2) for p,d in L.patrols]
P=L.start
for t,d in enumerate(r):
    P=L.adj[P][d]
    occ=[trs[k][t+1][0] for k in range(len(trs))]
    print(f'  m{t+1:2d} {d} P={P} pat={occ} {"HIT" if P in occ else ""}')
print('ACTIONS: '+game.actstr(r))
