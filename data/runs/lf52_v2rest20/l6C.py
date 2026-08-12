import drive
drive.click((15,5),'L6C: unload the green at (15,3) (select)'); drive.click((15,3),'L6C: land green at (15,3)')
drive.click((15,3),'L6C: green (15,3) consumes the green at (16,3) -> (17,3) (select)'); drive.click((17,3),'L6C: land at (17,3)')
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
drive.press(['ACTION4','ACTION4','ACTION1','ACTION1'],'L6C: bring the red-carrying shuttle to the (18,5) dock')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
drive.click((18,5),'L6C: unload the RED at (18,3) (select)'); drive.click((18,3),'L6C: land red at (18,3)')
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
