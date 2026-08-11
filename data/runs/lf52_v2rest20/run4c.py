import drive, nstate, subprocess, sys
PLAN=[('jump',(2,4),(3,4),(4,4)),('jump',(4,4),(5,4),(6,4)),('jump',(6,4),(7,4),(8,4)),
 ('press','ACTION4'),('press','ACTION4'),('press','ACTION4'),('press','ACTION4'),('press','ACTION4'),
 ('jump',(12,4),(13,4),(14,4)),('jump',(14,4),(14,5),(14,6)),('jump',(17,4),(17,5),(17,6)),
 ('jump',(17,6),(17,7),(17,8)),('jump',(17,8),(16,8),(15,8)),('jump',(14,6),(14,7),(14,8)),
 ('jump',(15,8),(14,8),(13,8)),
 ('press','ACTION3'),('press','ACTION3'),('press','ACTION3'),('press','ACTION3'),
 ('press','ACTION2'),('press','ACTION2'),
 ('press','ACTION4'),('press','ACTION4'),('press','ACTION4'),
 ('jump',(9,10),(9,11),(9,12)),
 ('press','ACTION3'),('press','ACTION3'),
 ('jump',(7,12),(7,13),(7,14)),
 ('press','ACTION3'),('press','ACTION3'),
 ('jump',(7,14),(6,14),(5,14)),('jump',(5,14),(5,13),(5,12)),
 ('jump',(5,12),(5,11),(5,10)),('jump',(5,10),(6,10),(7,10))]
# collapse consecutive presses into batches
steps=[]
for s in PLAN:
    if s[0]=='press' and steps and steps[-1][0]=='press': steps[-1][1].append(s[1])
    else: steps.append(['press',[s[1]]] if s[0]=='press' else list(s))
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
for i,s in enumerate(steps):
    if i<start: continue
    print('=== step',i,s)
    if s[0]=='press': drive.press(s[1],'L4 plan step %d: %s'%(i,' '.join(s[1])))
    else:
        _,a,m,l=s
        drive.click(a,'L4 plan step %d: jump %s over %s to %s (select)'%(i,a,m,l))
        drive.click(l,'L4 plan step %d: jump %s over %s to %s (land)'%(i,a,m,l))
        off,pegs,sh=drive.cur()
        print('   after: off',off,'pegs',sorted(pegs),'sh',sh)
print('DONE')
