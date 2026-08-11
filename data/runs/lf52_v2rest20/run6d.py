import drive
RAW=[('press','ACTION4')]*6+[('press','ACTION1')]*2+[('jump',(15,5),(15,4),(15,3))]+ \
    [('press','ACTION2')]*2+[('press','ACTION4')]+[('press','ACTION1')]*2+ \
    [('jump',(15,3),(16,3),(17,3)),('jump',(15,5),(15,4),(15,3))]
steps=[]
for s in RAW:
    if s[0]=='press' and steps and steps[-1][0]=='press': steps[-1][1].append(s[1])
    else: steps.append(['press',[s[1]]] if s[0]=='press' else list(s))
for i,s in enumerate(steps):
    print('=== step',i,s,flush=True)
    if s[0]=='press': drive.press(s[1],'L6d step %d: %s'%(i,' '.join(s[1])))
    else:
        _,a,m,l=s
        drive.click(a,'L6d step %d: jump %s over %s -> %s (select)'%(i,a,m,l))
        drive.click(l,'L6d step %d: land'%i)
        off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
