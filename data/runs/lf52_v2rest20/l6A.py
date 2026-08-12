import drive
JUMPS=[((3,3),(3,4),(3,5)),   # red down over green
       ((3,4),(3,5),(3,6)),   # green down over red
       ((3,5),(3,6),(3,7)),   # red down over green
       ((3,6),(3,7),(3,8)),   # green down over red
       ((2,8),(3,8),(4,8)),   # green consumes green
       ((4,9),(4,8),(4,7))]   # green consumes green
for i,(a,m,l) in enumerate(JUMPS):
    drive.click(a,'L6A jump %d: west reduction %s over %s -> %s (select)'%(i,a,m,l))
    drive.click(l,'L6A jump %d: land at %s'%(i,l))
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
