"""Execute a world-coordinate plan, correcting for camera scroll before every click."""
import subprocess, sys, parse, json
import nstate as state

def act(args, plan):
    cmd=['./act','do','--plan',plan]+args
    r=subprocess.run(cmd,capture_output=True,text=True)
    out=r.stdout+r.stderr
    print('  >',' '.join(args),'::',out.strip().splitlines()[0] if out.strip() else '(no output)')
    if 'stopped early' in out or 'score' in out:
        for l in out.strip().splitlines():
            if l.startswith('score=') or 'stopped early' in l: print('   ',l)
    return out

def cur():
    off,pegs,sh,f,reds=state.state()
    return off,pegs,sh

def screen_pt(cell,off):
    c,r=cell
    ox,oy=off
    x0,y0=6*c-ox, 6*r-oy
    # candidate pixels inside tile, prefer centre
    cands=[(x0+1,y0+1),(x0+2,y0+2),(x0+2,y0+1),(x0+1,y0+2),(x0,y0+1),(x0+3,y0+1),(x0+1,y0),(x0+1,y0+3),(x0,y0),(x0+3,y0+3)]
    for x,y in cands:
        if 0<=x<=63 and 1<=y<=63 and x0<=x<=x0+3 and y0<=y<=y0+3: return x,y
    return None

def click(cell,plantext):
    off,pegs,sh=cur()
    pt=screen_pt(cell,off)
    if pt is None:
        print('   !! cell',cell,'not visible at offset',off); sys.exit(1)
    act(['ACTION6:%d,%d'%pt], plantext+' [cell %s off=%s]'%(cell,off))

def press(actions,plantext):
    act(actions,plantext)
