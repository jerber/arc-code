import drive, sys
RAW=[('jump',(3,4),(3,5),(3,6)),('jump',(3,5),(3,6),(3,7)),('jump',(3,6),(3,7),(3,8)),
     ('jump',(2,8),(3,8),(4,8)),('jump',(4,9),(4,8),(4,7))]
for i,s in enumerate(RAW):
    print('=== step',i,s,flush=True)
    _,a,m,l=s
    drive.click(a,'L6 step %d: jump %s over %s -> %s (select)'%(i,a,m,l))
    drive.click(l,'L6 step %d: jump %s over %s -> %s (land)'%(i,a,m,l))
    off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
