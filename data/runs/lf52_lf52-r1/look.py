import sys
from wm import View,World
v=View('/tmp/cur.txt'); W=World()
off=W.align(v); W.merge(v,off)
def P(w): return (v.ox+6*(w[0]-off[0])+1, v.oy+6*(w[1]-off[1])+1)
print('camera off (world=screen+):',off,' ox,oy',v.ox,v.oy)
print('PEGS  ',sorted((X+off[0],Y+off[1]) for X,Y in v.peg))
print('SHUTS ',{(X+off[0],Y+off[1]):k for (X,Y),k in v.shut.items()})
print('restart-key visible:', sum(r.count('f') for r in v.g) % 12 != 0 or sum(r.count('f') for r in v.g)>200)
xs=[k[0] for k in W.map]; ys=[k[1] for k in W.map]
sym={'CELL':'.','WALL':'W','TRACK':'=','EMPTY':' '}
pegs={(X+off[0],Y+off[1]) for X,Y in v.peg}
shut={(X+off[0],Y+off[1]):k for (X,Y),k in v.shut.items()}
print('    '+''.join(str(x%10) for x in range(min(xs),max(xs)+1)))
for Y in range(min(ys),max(ys)+1):
    r=''
    for X in range(min(xs),max(xs)+1):
        if (X,Y) in pegs: r+='P'
        elif (X,Y) in shut: r+={'SWALL':'#','SPEG':'@','SHUTTLE':'o'}[shut[(X,Y)]]
        else: r+=sym.get(W.map.get((X,Y)),'?')
    print(f'{Y:3d} '+r)
for a in sys.argv[1:]:
    x,y=a.split(','); print(f'({x},{y}) ->',P((int(x),int(y))))
