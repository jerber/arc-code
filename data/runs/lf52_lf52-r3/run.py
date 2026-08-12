import subprocess,sys,game,world
def act(args,plan):
    r=subprocess.run(['./act','do','--plan',plan]+args,capture_output=True,text=True)
    print(' ',' '.join(args[:6]),('...' if len(args)>6 else ''),r.stdout.strip().split('\n')[-1] if r.stdout else r.stderr[:120])
    return r.stdout

def run(path=None,dry=False):
    E=game.extract()
    if path is None:
        path=game.solve(E)
        if not path: print('no solution'); return
    print('plan length',len(path))
    i=0
    while i<len(path):
        mv=path[i]
        if mv[0]!='JUMP':
            grp=[]
            while i<len(path) and path[i][0]!='JUMP':
                grp.append(path[i][0]); i+=1
            if not dry: act(grp,'auto: shuttle moves %s'%(' '.join(grp)))
        else:
            _,a,b,c=mv; i+=1
            E=game.extract()
            ox,oy=E['off']
            sa=(a[0]-ox+1,a[1]-oy+1); sc=(c[0]-ox+1,c[1]-oy+1)
            if not(0<=sa[0]<64 and 0<=sa[1]<64 and 0<=sc[0]<64 and 0<=sc[1]<64):
                print('OFF SCREEN',a,c,'off',E['off']); return
            if not dry: act(['ACTION6:%d,%d'%sa,'ACTION6:%d,%d'%sc],'auto: jump %s over %s to %s'%(a,b,c))
    print('done')
if __name__=='__main__': run(dry='-n' in sys.argv)
