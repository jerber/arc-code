import drive
RAW=[('jump',(3,7),(4,7),(5,7)),('jump',(4,7),(5,7),(6,7)),('jump',(5,7),(6,7),(7,7)),('jump',(6,7),(7,7),(8,7))]
for i,s in enumerate(RAW):
    print('=== step',i,s,flush=True)
    _,a,m,l=s
    drive.click(a,'L6b step %d: leapfrog red/green: jump %s over %s -> %s (select)'%(i,a,m,l))
    drive.click(l,'L6b step %d: jump %s over %s -> %s (land)'%(i,a,m,l))
    off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
