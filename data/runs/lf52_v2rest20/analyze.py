import parse,collections,sys
hdr,rows=parse.last()
g=[[int(c,16) for c in r] for r in rows]
print(hdr)
# report bounding boxes of each color
loc=collections.defaultdict(list)
for y in range(64):
    for x in range(64):
        loc[g[y][x]].append((x,y))
for v,ps in sorted(loc.items()):
    xs=[p[0] for p in ps]; ys=[p[1] for p in ps]
    print(f"val {v:x} count {len(ps):5d} bbox x{min(xs)}-{max(xs)} y{min(ys)}-{max(ys)}")
