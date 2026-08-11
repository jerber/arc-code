import drive, sys
RAW=[('press','ACTION3'),('press','ACTION3'),('press','ACTION3'),('press','ACTION3'),('press','ACTION3'),
('press','ACTION3'),('press','ACTION3'),('press','ACTION1'),('press','ACTION1'),
('jump',(13,4),(14,4),(15,4)),
('press','ACTION1'),('press','ACTION1'),('press','ACTION4'),('press','ACTION4'),('press','ACTION4'),('press','ACTION4'),
('press','ACTION2'),('press','ACTION2'),
('jump',(15,4),(16,4),(17,4)),('jump',(17,4),(18,4),(19,4)),
('press','ACTION1'),('press','ACTION1'),('press','ACTION4'),
('jump',(19,5),(19,4),(19,3)),('jump',(19,3),(19,2),(19,1)),
('press','ACTION3'),('press','ACTION3'),('press','ACTION3'),
('jump',(20,1),(19,1),(18,1)),('jump',(18,1),(17,1),(16,1)),('jump',(16,1),(16,2),(16,3)),
('press','ACTION3'),('press','ACTION3'),('press','ACTION2'),('press','ACTION2'),('press','ACTION2'),('press','ACTION2'),
('press','ACTION4'),('press','ACTION4'),
('jump',(16,3),(16,4),(16,5)),('jump',(16,5),(16,6),(16,7)),('jump',(16,7),(16,8),(16,9)),
('jump',(17,9),(16,9),(15,9))]
steps=[]
for s in RAW:
    if s[0]=='press' and steps and steps[-1][0]=='press': steps[-1][1].append(s[1])
    else: steps.append(['press',[s[1]]] if s[0]=='press' else list(s))
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
for i,s in enumerate(steps):
    if i<start: continue
    print('=== step',i,s,flush=True)
    if s[0]=='press': drive.press(s[1],'L5c step %d: %s'%(i,' '.join(s[1])))
    else:
        _,a,m,l=s
        drive.click(a,'L5c step %d: jump %s over %s -> %s (select)'%(i,a,m,l))
        drive.click(l,'L5c step %d: jump %s over %s -> %s (land)'%(i,a,m,l))
        off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
        if l not in pegs and sh.get(l)!='peg':
            print('   !! expected peg at',l,'ABORT'); sys.exit(1)
print('DONE')
