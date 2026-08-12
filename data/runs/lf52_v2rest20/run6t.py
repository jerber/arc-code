import drive
drive.press(['ACTION4','ACTION1','ACTION1'],'L6t: bring loaded west shuttle B to the (15,5) dock')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
drive.click((15,5),'L6t: unload B green over pivot (15,4) -> (15,3) (select)')
drive.click((15,3),'L6t: land green at (15,3)')
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
drive.press(['ACTION2','ACTION2','ACTION4','ACTION3','ACTION1','ACTION1'],'L6t: jog the loaded east shuttle horizontally to pull the camera east, then back to the (24,5) dock')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
