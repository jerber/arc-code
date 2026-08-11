import drive, state, sys, time
PLAN=[
 ('jump',(2,2),(2,3),(2,4),'R1 a: (2,2) over (2,3) -> (2,4)'),
 ('jump',(2,4),(3,4),(4,4),'R1 b: (2,4) over (3,4) -> (4,4)'),
 ('jump',(4,4),(4,3),(4,2),'R1 c: (4,4) over (4,3) -> (4,2)'),
 ('press',['ACTION3'],'dock shuttle1 at (6,2) (shuttle2 slides to (5,8))'),
 ('jump',(4,2),(5,2),(6,2),'E1: export region1 peg into shuttle1 at (6,2)'),
 ('press',['ACTION4','ACTION4','ACTION4'],'drive shuttle1 to (9,2) dock at big right panel'),
 ('jump',(13,3),(12,3),(11,3),'R0 d: (13,3) over (12,3) -> (11,3)'),
 ('jump',(13,5),(12,5),(11,5),'R0 e: (13,5) over (12,5) -> (11,5)'),
 ('jump',(9,2),(10,2),(11,2),'I1: shuttle1 peg jumps over (10,2) into (11,2)'),
 ('jump',(11,2),(11,3),(11,4),'R0 g'),
 ('jump',(11,4),(11,5),(11,6),'R0 h'),
 ('jump',(11,6),(11,7),(11,8),'R0 i'),
 ('press',['ACTION1','ACTION1','ACTION4','ACTION4','ACTION2','ACTION2','ACTION4'],'drive shuttle2 around loop to (10,8) dock'),
 ('jump',(12,8),(11,8),(10,8),'E2: export region0 peg into shuttle2'),
 ('press',['ACTION3','ACTION1','ACTION1','ACTION3','ACTION3','ACTION2','ACTION2','ACTION3','ACTION3'],'drive loaded shuttle2 back to (5,8) dock at region2'),
 ('jump',(5,8),(4,8),(3,8),'I2: shuttle2 peg jumps over (4,8) into (3,8)'),
 ('jump',(3,8),(2,8),(1,8),'FINAL: (3,8) over (2,8) -> (1,8), 1 peg left'),
]
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
for i,step in enumerate(PLAN):
    if i<start: continue
    print('=== step',i,step[-1])
    if step[0]=='press':
        drive.press(step[1],'L3 plan: '+step[2])
    else:
        _,a,m,l,txt=step
        drive.click(a,'L3 plan: '+txt+' (select)')
        drive.click(l,'L3 plan: '+txt+' (land)')
        off,pegs,sh=drive.cur()
        print('   after: pegs',len(pegs),'sh',sh,'off',off)
        if l not in pegs and l not in sh:
            print('   !! expected peg at',l,'- ABORT'); sys.exit(1)
print('plan complete')
