import drive
RAW=[('jump',(16,3),(17,3),(18,3)),('jump',(17,3),(18,3),(19,3)),('jump',(18,3),(19,3),(20,3)),
     ('jump',(19,3),(20,3),(21,3)),('jump',(20,3),(21,3),(22,3))]
for i,s in enumerate(RAW):
    print('=== step',i,s,flush=True)
    _,a,m,l=s
    drive.click(a,'L6e step %d: leapfrog east: jump %s over %s -> %s (select)'%(i,a,m,l))
    drive.click(l,'L6e step %d: land'%i)
    off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
