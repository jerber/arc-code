import drive, state
PLAN=[
 ('press',['ACTION4','ACTION4','ACTION4','ACTION4'],'drive loaded shuttle1 to (12,4) dock (shuttle2 slides right to (13,8))'),
 ('jump',(12,4),(13,4),(14,4),'unload: shuttle1 peg over (13,4) -> (14,4)'),
 ('jump',(14,4),(14,5),(14,6),'traveller jumps over purple pivot (14,5) -> (14,6)'),
 ('jump',(14,6),(14,7),(14,8),'traveller jumps over purple pivot (14,7) -> (14,8)'),
]
for i,step in enumerate(PLAN):
    print('=== step',i,step[-1])
    if step[0]=='press': drive.press(step[1],'L4: '+step[2])
    else:
        _,a,m,l,txt=step
        drive.click(a,'L4: '+txt+' (select)')
        drive.click(l,'L4: '+txt+' (land)')
        off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh)
