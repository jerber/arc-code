import sys, re

def blocks(path='logs.txt'):
    """Yield (header, plan_lines, {tag: [rows]}) per action block."""
    txt = open(path).read()
    parts = txt.split('='*80)
    out = []
    for p in parts[1:]:
        lines = p.split('\n')
        hdr = None
        grids = {}
        cur = None
        plan = []
        for ln in lines:
            if hdr is None and ln.strip().startswith('action'):
                hdr = ln.strip(); continue
            m = re.match(r'^\[(.*?)\]$', ln.strip())
            if m:
                cur = m.group(1); grids.setdefault(cur, [])
                continue
            if cur is not None and re.fullmatch(r'[0-9a-f]+', ln.strip()):
                grids[cur].append(ln.strip())
            elif hdr is not None and cur is None and ln.strip():
                plan.append(ln.strip())
        if hdr: out.append((hdr, plan, grids))
    return out

def lastgrid(path='logs.txt'):
    bs = blocks(path)
    hdr, plan, grids = bs[-1]
    key = 'final' if 'final' in grids else list(grids)[-1]
    # choose last non-anim key preference
    for k in ['final','board']:
        if k in grids and grids[k]: key=k; break
    return hdr, grids[key]

if __name__=='__main__':
    hdr, g = lastgrid()
    print(hdr, 'rows', len(g), 'cols', len(g[0]) if g else 0)

def show(g, x0=0,y0=0,x1=64,y1=64,step=1):
    print('    '+''.join(str(x%10) for x in range(x0,x1,step)))
    for y in range(y0,y1,step):
        print(f'{y:3d} '+''.join(g[y][x] for x in range(x0,x1,step)))

def counts(g):
    from collections import Counter
    c=Counter(''.join(g))
    return dict(sorted(c.items()))
