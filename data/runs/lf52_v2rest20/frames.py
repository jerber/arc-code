import re,sys
txt=open('logs.txt').read()
parts=txt.split('='*80)
idx=int(sys.argv[1])
p=parts[idx+1] if idx>=0 else parts[idx]
lines=p.strip('\n').split('\n')
print(lines[0])
frames=[];cur=None;name=None
for l in lines:
    if l.startswith('[anim') or l.startswith('[final'):
        if cur is not None: frames.append((name,cur))
        name=l.strip(); cur=[]
    elif re.fullmatch(r'[0-9a-f]{64}',l) and cur is not None:
        cur.append(l)
if cur: frames.append((name,cur))
print('frames',[(n,len(r)) for n,r in frames])
prev=None
for n,r in frames:
    if prev is None: prev=r; print(n,'(base)'); continue
    ch=[(x,y,prev[y][x],r[y][x]) for y in range(64) for x in range(64) if prev[y][x]!=r[y][x] and y>0]
    import collections
    reg=collections.defaultdict(list)
    for x,y,f,t in ch: reg[(f,t)].append((x,y))
    print(n,'changes',len(ch))
    for k,v in sorted(reg.items()):
        xs=[q[0] for q in v];ys=[q[1] for q in v]
        print('   ',k,len(v),'x%d-%d y%d-%d'%(min(xs),max(xs),min(ys),max(ys)))
    prev=r
