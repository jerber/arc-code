import drive, sys
PLAN=[('press','ACTION3'),('press','ACTION3'),('press','ACTION2'),('press','ACTION4'),('press','ACTION4'),
 ('press','ACTION4'),('press','ACTION2'),('press','ACTION2'),
 ('jump',(2,4),(3,4),(4,4)),('jump',(4,4),(5,4),(6,4)),
 ('press','ACTION2'),('jump',(7,4),(6,4),(5,4))]
steps=[]
for s in PLAN:
    if s[0]=='press' and steps and steps[-1][0]=='press': steps[-1][1].append(s[1])
    else: steps.append(['press',[s[1]]] if s[0]=='press' else list(s))
for i,s in enumerate(steps):
    print('=== step',i,s)
    if s[0]=='press': drive.press(s[1],'L5 plan %d: %s'%(i,' '.join(s[1])))
    else:
        _,a,m,l=s
        drive.click(a,'L5 plan %d: jump %s over %s -> %s (select)'%(i,a,m,l))
        drive.click(l,'L5 plan %d: jump %s over %s -> %s (land)'%(i,a,m,l))
        off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh)
