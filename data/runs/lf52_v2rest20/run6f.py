import drive
RAW=[('press','ACTION4'),('press','ACTION4'),('press','ACTION1'),('press','ACTION1'),
     ('jump',(20,3),(19,3),(18,3)),('jump',(18,3),(18,4),(18,5))]
steps=[]
for s in RAW:
    if s[0]=='press' and steps and steps[-1][0]=='press': steps[-1][1].append(s[1])
    else: steps.append(['press',[s[1]]] if s[0]=='press' else list(s))
for i,s in enumerate(steps):
    print('=== step',i,s,flush=True)
    if s[0]=='press': drive.press(s[1],'L6f step %d: %s'%(i,' '.join(s[1])))
    else:
        _,a,m,l=s
        drive.click(a,'L6f step %d: jump %s over %s -> %s (select)'%(i,a,m,l)); drive.click(l,'L6f step %d: land'%i)
        off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
