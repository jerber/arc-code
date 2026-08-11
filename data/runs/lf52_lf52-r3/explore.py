import subprocess,sys,json
import world,game
def act(args,plan):
    r=subprocess.run(['./act','do','--plan',plan]+args,capture_output=True,text=True)
    return r.stdout
def known(E):
    return len(E['cells'])+len(E['nodes'])+len(E['pivots'])
def main(rounds=3,k=6):
    E=game.extract(); prev=known(E)
    print('start known',prev,'shut',E['shut'])
    for r in range(rounds):
        grew=False
        for d in ['ACTION3','ACTION1','ACTION4','ACTION2']:
            out=act([d]*k,'explore round %d dir %s'%(r,d))
            E=game.extract(); n=known(E)
            print(' ',d,'known',n,'shut',E['shut'],'off',E['off'])
            if n>prev: grew=True
            prev=n
        if not grew:
            print('no growth, stop'); break
if __name__=='__main__': main(int(sys.argv[1]) if len(sys.argv)>1 else 3, int(sys.argv[2]) if len(sys.argv)>2 else 6)
