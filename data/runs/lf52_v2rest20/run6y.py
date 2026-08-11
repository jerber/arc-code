import drive
drive.press(['ACTION3','ACTION3','ACTION3','ACTION1','ACTION1'],'L6y: bring loaded shuttle A to the (15,5) dock')
drive.click((15,5),'L6y: unload the green over pivot (15,4) -> (15,3) (select)')
drive.click((15,3),'L6y: land green at (15,3)')
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
JUMPS=[((15,3),(16,3),(17,3)),((16,3),(17,3),(18,3)),((17,3),(18,3),(19,3)),((18,3),(19,3),(20,3)),
       ((19,3),(20,3),(21,3)),((20,3),(21,3),(22,3)),((21,3),(22,3),(23,3)),((22,3),(23,3),(24,3))]
for i,(a,m,l) in enumerate(JUMPS):
    drive.click(a,'L6y jump %d: leapfrog green+red east (select)'%i)
    drive.click(l,'L6y jump %d: land at %s'%(i,l))
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
