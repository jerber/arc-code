import drive
JUMPS=[((3,3),(3,4),(3,5)),((3,4),(3,5),(3,6)),((3,5),(3,6),(3,7)),((3,6),(3,7),(3,8)),
       ((2,8),(3,8),(4,8)),((4,9),(4,8),(4,7)),
       ((3,7),(4,7),(5,7)),((4,7),(5,7),(6,7)),((5,7),(6,7),(7,7))]
for i,(a,m,l) in enumerate(JUMPS):
    drive.click(a,'L6W jump %d: west phase -> green (6,7), red (7,7) (select)'%i)
    drive.click(l,'L6W jump %d: land at %s'%(i,l))
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
