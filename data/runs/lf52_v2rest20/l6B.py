import drive
JUMPS=[((3,7),(4,7),(5,7)),((4,7),(5,7),(6,7)),((5,7),(6,7),(7,7)),
       ((6,7),(7,7),(8,7)),   # green boards shuttle at (8,7)
       ((7,7),(8,7),(9,7))]   # red jumps over the loaded shuttle into the second shuttle
for i,(a,m,l) in enumerate(JUMPS):
    drive.click(a,'L6B jump %d: leapfrog to the dock and board the shuttles (select)'%i)
    drive.click(l,'L6B jump %d: land at %s'%(i,l))
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
drive.press(['ACTION4']*7,'L6B: drive both loaded shuttles east')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
drive.press(['ACTION1','ACTION1'],'L6B: raise the green-carrying shuttle to the (15,5) dock')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
