import drive
drive.press(['ACTION3']*9,'L6c: drive both shuttles left so the loaded one is at (8,7) and the empty at (9,7)')
a,m,l=(7,7),(8,7),(9,7)
drive.click(a,'L6c: red (7,7) jumps over the loaded shuttle at (8,7) into the empty shuttle at (9,7) (select)')
drive.click(l,'L6c: land red in shuttle (9,7)')
off,pegs,sh=drive.cur(); print('after: off',off,'pegs',sorted(pegs),'sh',sh)
