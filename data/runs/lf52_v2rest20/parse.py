import re,sys,collections
def blocks(path='logs.txt'):
    """yield (header, [final board rows]) for each action block"""
    txt=open(path).read()
    parts=txt.split('='*80)
    out=[]
    for p in parts[1:]:
        lines=p.strip('\n').split('\n')
        hdr=lines[0].strip()
        # find last [final] or last anim
        idx=None
        for i,l in enumerate(lines):
            if l.startswith('[final]'): idx=i
        if idx is None:
            # take last [anim ...]
            for i,l in enumerate(lines):
                if l.startswith('[anim'): idx=i
        if idx is None: continue
        rows=[l for l in lines[idx+1:] if re.fullmatch(r'[0-9a-f]{64}',l)]
        out.append((hdr,rows))
    return out
def last(path='logs.txt'):
    b=blocks(path)
    return b[-1]
if __name__=='__main__':
    bs=blocks()
    print('n blocks',len(bs))
    hdr,rows=bs[-1]
    print(hdr, 'rows',len(rows))
