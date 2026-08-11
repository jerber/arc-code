import drive
drive.click((18,3),'L6D: load the RED at (18,3) into the shuttle at (18,5) - test whether the camera centres on the loaded shuttle (select)')
drive.click((18,5),'L6D: land red in the shuttle')
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
