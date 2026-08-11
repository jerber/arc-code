import drive
PLAN=[
 ('jump',(12,4),(13,4),(14,4),'unload shuttle1 peg over (13,4) -> (14,4)'),
 ('jump',(14,4),(14,5),(14,6),'P1 over pivot (14,5) -> (14,6)'),
 ('jump',(14,6),(14,7),(14,8),'P1 over pivot (14,7) -> (14,8)'),
 ('jump',(17,4),(17,5),(17,6),'P3 over pivot (17,5) -> (17,6)'),
 ('jump',(17,6),(17,7),(17,8),'P3 over pivot (17,7) -> (17,8)'),
 ('jump',(17,8),(16,8),(15,8),'P3 over pivot (16,8) -> (15,8)'),
 ('jump',(15,8),(14,8),(13,8),'P3 jumps over P1 into shuttle2 at (13,8): P1 consumed, shuttle loaded'),
]
for i,step in enumerate(PLAN):
    print('=== step',i,step[-1])
    _,a,m,l,txt=step
    drive.click(a,'L4: '+txt+' (select)')
    drive.click(l,'L4: '+txt+' (land)')
    off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh)
