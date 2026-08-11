import drive
PLAN=[('press',['ACTION4','ACTION2']),('jump',(11,4),(12,4),(13,4))]
for i,s in enumerate(PLAN):
    print('=== step',i,s)
    if s[0]=='press': drive.press(s[1],'L5b: dock loaded shuttle at (11,4)')
    else:
        _,a,m,l=s
        drive.click(a,'L5b: jump %s over %s -> %s (select)'%(a,m,l))
        drive.click(l,'L5b: jump %s over %s -> %s (land)'%(a,m,l))
        off,pegs,sh=drive.cur(); print('   after: off',off,'pegs',sorted(pegs),'sh',sh)
