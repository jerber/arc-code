"""Execute a corridor plan step by step with live camera verification."""
import subprocess,sys,json,numpy as np,fastfit,re
DOCK={(15,3):(15,5),(18,3):(18,5),(24,3):(24,5)}
def board():
    r=subprocess.run(['./act','board'],capture_output=True,text=True)
    rows=[l for l in r.stdout.splitlines() if len(l)==64 and all(c in '0123456789abcdef' for c in l)]
    if len(rows)!=64: raise SystemExit('board read failed: %r'%r.stdout[:200])
    return np.array([[int(c,16) for c in row] for row in rows],dtype=np.int16)
def cam():
    f=fastfit.fitx(board())
    return f[1],f
def pix(cell,c):
    x0=6*cell[0]-c; y0=6*cell[1]
    for dx,dy in ((1,1),(2,2),(2,1),(1,2),(0,1),(3,1),(0,2),(3,2),(1,0),(1,3),(0,0),(3,3)):
        x,y=x0+dx,y0+dy
        if 0<=x<=63 and 1<=y<=63: return x,y
    return None
def act(args,plan):
    r=subprocess.run(['./act','do','--plan',plan]+args,capture_output=True,text=True)
    out=(r.stdout+r.stderr).strip()
    if 'not found' in out or 'act:' in out: print('  !!',out.splitlines()[0]); return False,out
    return True,out
def click(cell,plan):
    c,_=cam()
    p=pix(cell,c)
    if p is None: print('  !! cell',cell,'not visible at cam',c); return False
    ok,out=act(['ACTION6:%d,%d'%p],plan+' [cell %s cam=%d]'%(cell,c))
    return ok
def run(steps,tag):
    for i,s in enumerate(steps):
        print('step %d/%d: %s'%(i+1,len(steps),s))
        if s.startswith('P'):
            ok,_=act(['ACTION%s'%s[1]],'%s step %d: press %s'%(tag,i+1,s))
            if not ok: return False
        else:
            kind=s[0]; who=s[1]
            if kind in 'LU':
                cell=eval(s[2:]); dock=DOCK[cell]
                a,b=(cell,dock) if kind=='L' else (dock,cell)
            else:
                m=re.match(r'J.\((\d+), (\d+)\)>\((\d+), (\d+)\)',s)
                a=(int(m.group(1)),int(m.group(2))); b=(int(m.group(3)),int(m.group(4)))
            if not click(a,'%s step %d %s: select'%(tag,i+1,s)): return False
            if not click(b,'%s step %d %s: land'%(tag,i+1,s)): return False
        c,f=cam(); print('   cam=%d fit=%s'%(c,f[3]))
    return True
if __name__=='__main__':
    steps=json.load(open(sys.argv[1]))
    run(steps,sys.argv[2] if len(sys.argv)>2 else 'L6')
