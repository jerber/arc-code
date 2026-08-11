import wparse,sys
g=wparse.load()
cells,track,conn,tconn,known=wparse.parse(g)
cs=[c for c,r in cells|track]; rs=[r for c,r in cells|track]
print('cells',len(cells),'track',len(track))
print('    '+''.join(str(c%10) for c in range(min(cs)-1,max(cs)+2)))
for r in range(min(rs)-1,max(rs)+2):
    line=''
    for c in range(min(cs)-1,max(cs)+2):
        k=(c,r)
        line += '#' if k in cells else ('+' if k in track else ('?' if k not in known else '.'))
    print('%3d %s'%(r,line))
