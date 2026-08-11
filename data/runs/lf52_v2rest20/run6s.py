import drive, sys
RAW=[('press','ACTION3'),('press','ACTION3'),('press','ACTION3'),('press','ACTION1'),('press','ACTION1'),
('jump',(24,5),(24,4),(24,3)),('jump',(24,3),(23,3),(22,3)),('jump',(23,3),(22,3),(21,3)),
('jump',(22,3),(21,3),(20,3)),('jump',(21,3),(20,3),(19,3)),('jump',(20,3),(19,3),(18,3)),
('jump',(19,3),(18,3),(17,3)),('jump',(18,3),(17,3),(16,3)),('jump',(17,3),(16,3),(15,3)),
('jump',(15,3),(15,4),(15,5)),
('press','ACTION2'),('press','ACTION2'),('press','ACTION4'),('press','ACTION1'),('press','ACTION1'),
('jump',(15,5),(15,4),(15,3)),('jump',(15,3),(16,3),(17,3))]
steps=[]
for s in RAW:
    if s[0]=='press' and steps and steps[-1][0]=='press': steps[-1][1].append(s[1])
    else: steps.append(['press',[s[1]]] if s[0]=='press' else list(s))
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
for i,s in enumerate(steps):
    if i<start: continue
    print('=== step',i,s,flush=True)
    if s[0]=='press': drive.press(s[1],'L6s step %d: %s'%(i,' '.join(s[1])))
    else:
        _,a,m,l=s
        drive.click(a,'L6s step %d: jump %s over %s -> %s (select)'%(i,a,m,l))
        drive.click(l,'L6s step %d: land'%i)
        off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
