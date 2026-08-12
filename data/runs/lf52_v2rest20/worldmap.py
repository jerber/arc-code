"""Render the merged worldmap.txt as a cell map in world coordinates."""
canvas=open('worldmap.txt').read().split('\n')
H=len(canvas); W=len(canvas[0])
OFF=40
g=[[int(c,16) if c in '0123456789abcdef' else -1 for c in row] for row in canvas]
def cell(c,r):
    """classify world cell (c,r)"""
    x0,y0=6*c+OFF, 6*r+OFF
    if not(0<=x0<W-3 and 0<=y0<H-3): return ' '
    vals=[g[y0+j][x0+i] for j in range(4) for i in range(4)]
    if -1 in vals: return '?'
    s=set(vals)
    if s<={1,0xe,2}: return 'O' if 0xe in s else '.'
    if s<={0xc,0xe}: return 'S' if 0xe in s else 's'
    if all(g[y0+j][x0+i]==5 for j in (1,2) for i in (1,2)): return '+'
    return ' '
cs=range(-2,20); rs=range(-1,14)
print('     '+''.join('%d'%(c%10) for c in cs))
for r in rs:
    print('%3d  %s'%(r,''.join(cell(c,r) for c in cs)))
