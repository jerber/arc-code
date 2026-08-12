"""Replay the recorded level 1-5 solution, one batch per level, verifying score."""
import json,subprocess,sys,re
R=json.load(open('mined.json'))
seq={}
for r in R:
    if r['n']==0: continue
    seq.setdefault(r['lvl'],[]).append(r['act'])
def conv(a):
    m=re.match(r'ACTION6 x=(\d+) y=(\d+)',a)
    return 'ACTION6:%s,%s'%(m.group(1),m.group(2)) if m else a
def status():
    out=subprocess.run(['./act','status'],capture_output=True,text=True).stdout
    m=re.search(r'score=(\d+)/\d+ level=(\d+).*actions=(\d+)',out)
    return (int(m.group(1)),int(m.group(2)),int(m.group(3))) if m else None
for lvl in (1,2,3,4,5):
    acts=[conv(a) for a in seq[lvl]]
    print('== replay level',lvl,len(acts),'actions; status before',status())
    # send in chunks of 20 so a mid-batch score change wastes little
    i=0
    while i<len(acts):
        chunk=acts[i:i+20]
        r=subprocess.run(['./act','do','--plan','replay recorded solution for level %d (steps %d-%d)'%(lvl,i+1,i+len(chunk))]+chunk,capture_output=True,text=True)
        out=(r.stdout+r.stderr).strip()
        if 'act:' in out: print('  ERROR',out.splitlines()[0]); sys.exit(1)
        st=status(); print('  after chunk %d: %s'%(i//20,st))
        if st[1]>lvl: break
        i+=len(chunk)
    print('  level',lvl,'done, status',status())
print('replay complete',status())
