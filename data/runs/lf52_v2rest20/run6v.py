import drive
drive.press(['ACTION4','ACTION4','ACTION1','ACTION1'],'L6v: bring the red-carrying shuttle to the (18,5) dock')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
drive.click((18,5),'L6v: unload the RED over pivot (18,4) -> (18,3) (select)')
drive.click((18,3),'L6v: land red at (18,3)')
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
for i,(a,m,l) in enumerate([((17,3),(18,3),(19,3)),((18,3),(19,3),(20,3)),((19,3),(20,3),(21,3)),
                            ((20,3),(21,3),(22,3)),((21,3),(22,3),(23,3))]):
    drive.click(a,'L6v: leapfrog green/red east (select)')
    drive.click(l,'L6v: land at %s'%(l,))
off,pegs,sh=drive.cur(); print('   after leapfrog: off',off,'pegs',sorted(pegs),flush=True)
drive.click((23,3),'L6v: click the green at (23,3) - does the game offer a jump across the gap at (23,4) to (23,5)?')
