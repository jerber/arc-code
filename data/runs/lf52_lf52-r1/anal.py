import re,sys
from collections import deque,Counter

def grid(path='/tmp/b.txt'):
    L=[l.strip() for l in open(path)]
    return [l for l in L if re.fullmatch(r'[0-9a-f]{64}',l)]

def comps(g,chars):
    seen=[[0]*64 for _ in range(64)]; out=[]
    for y in range(64):
        for x in range(64):
            if g[y][x] in chars and not seen[y][x]:
                q=deque([(x,y)]); seen[y][x]=1; cs=[]
                while q:
                    cx,cy=q.popleft(); cs.append((cx,cy))
                    for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
                        nx,ny=cx+dx,cy+dy
                        if 0<=nx<64 and 0<=ny<64 and g[ny][nx] in chars and not seen[ny][nx]:
                            seen[ny][nx]=1; q.append((nx,ny))
                out.append(cs)
    return out

def analyze(g):
    tiles=[]
    for cs in comps(g,set('1e23')):
        xs=[c[0] for c in cs]; ys=[c[1] for c in cs]
        tiles.append((min(xs),min(ys),max(xs),max(ys),len(cs),Counter(g[y][x] for x,y in cs)))
    boxes=[]
    for cs in comps(g,set('c')):
        xs=[c[0] for c in cs]; ys=[c[1] for c in cs]
        boxes.append((min(xs),min(ys),max(xs),max(ys),len(cs)))
    return tiles,boxes

if __name__=='__main__':
    g=grid(sys.argv[1] if len(sys.argv)>1 else '/tmp/b.txt')
    tiles,boxes=analyze(g)
    print('TILES',len(tiles))
    for t in tiles:
        peg='P' if 'e' in t[5] else ('G' if '2' in t[5] else '.')
        print(f'  ({t[0]},{t[1]})-({t[2]},{t[3]}) n={t[4]} {peg}')
    print('BOXES',len(boxes))
    for b in boxes: print(' ',b)
    print('offsets x%6:',Counter(t[0]%6 for t in tiles),'y%6:',Counter(t[1]%6 for t in tiles))
