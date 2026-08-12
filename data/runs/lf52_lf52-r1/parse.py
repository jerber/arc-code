import re,sys

def load_states(path='logs.txt'):
    """Return list of (header, plan, final_grid) blocks."""
    txt=open(path).read()
    blocks=txt.split('='*80)
    out=[]
    for b in blocks:
        lines=b.strip('\n').split('\n')
        if not lines or not lines[0].startswith('action'): continue
        hdr=lines[0]
        # find [final] else last [anim]
        idx=None
        for i,l in enumerate(lines):
            if l.strip()=='[final]': idx=i
        if idx is None:
            for i,l in enumerate(lines):
                if l.startswith('[anim'): idx=i
        if idx is None: continue
        grid=[]
        for l in lines[idx+1:]:
            if re.fullmatch(r'[0-9a-f]{64}',l.strip()): grid.append(l.strip())
            elif grid: break
        plan='\n'.join(l for l in lines[1:idx] if not l.startswith('[') and l.strip())
        out.append((hdr,plan,grid))
    return out

def diff(g1,g2):
    d=[]
    for y in range(len(g1)):
        for x in range(64):
            if g1[y][x]!=g2[y][x]: d.append((x,y,g1[y][x],g2[y][x]))
    return d

if __name__=='__main__':
    S=load_states()
    print(len(S),'states')
    for h,p,g in S[-3:]:
        print(h, len(g))
