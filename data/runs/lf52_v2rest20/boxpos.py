import parse
h,r=parse.last()
cells=[(x,y) for y in range(64) for x in range(64) if r[y][x] in 'bc']
if not cells: print('no box'); raise SystemExit
xs=[c[0] for c in cells]; ys=[c[1] for c in cells]
print(h)
print('box bbox x%d-%d y%d-%d center %.1f,%.1f'%(min(xs),max(xs),min(ys),max(ys),(min(xs)+max(xs))/2,(min(ys)+max(ys))/2))
