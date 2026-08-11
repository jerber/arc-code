import drive
for i,(a,m,l) in enumerate([((18,3),(19,3),(20,3)),((19,3),(20,3),(21,3))]):
    drive.click(a,'L6i step %d: leapfrog east (select)'%i)
    drive.click(l,'L6i step %d: land'%i)
    off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),flush=True)
