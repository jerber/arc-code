import drive
JUMPS=[((24,3),(23,3),(22,3)),((23,3),(22,3),(21,3)),((22,3),(21,3),(20,3)),((21,3),(20,3),(19,3)),
       ((20,3),(19,3),(18,3)),((19,3),(18,3),(17,3)),((18,3),(17,3),(16,3)),((17,3),(16,3),(15,3))]
for i,(a,m,l) in enumerate(JUMPS):
    drive.click(a,'L6x step %d: leapfrog green+red west along row 3 (select)'%i)
    drive.click(l,'L6x step %d: land at %s'%(i,l))
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
drive.click((15,3),'L6x: load the green at (15,3) into shuttle A at (15,5) - small camera lock (select)')
drive.click((15,5),'L6x: land in A')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
drive.press(['ACTION2','ACTION2','ACTION4','ACTION4','ACTION4'],'L6x: drive A east to col 18 - camera should jump to ~104')
off,pegs,sh=drive.cur(); print('   FINAL off',off,'sh',sh,flush=True)
