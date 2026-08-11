import drive
JUMPS=[((18,3),(19,3),(20,3)),((19,3),(20,3),(21,3)),((20,3),(21,3),(22,3)),
       ((21,3),(22,3),(23,3)),((22,3),(23,3),(24,3))]
for i,(a,m,l) in enumerate(JUMPS):
    drive.click(a,'L6n step %d: leapfrog green/red east along row 3 (select)'%i)
    drive.click(l,'L6n step %d: land at %s'%(i,l))
off,pegs,sh=drive.cur(); print('   after leapfrog: off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
drive.press(['ACTION2','ACTION2','ACTION2','ACTION2'],'L6n: east shuttle down the col-26 track')
drive.press(['ACTION3','ACTION3'],'L6n: east shuttle west along row 7 to (24,7)')
drive.press(['ACTION1','ACTION1'],'L6n: east shuttle up to the (24,5) dock')
off,pegs,sh=drive.cur(); print('   shuttles: off',off,'sh',sh,flush=True)
