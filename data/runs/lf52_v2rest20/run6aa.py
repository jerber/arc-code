import drive
drive.press(['ACTION2']*4+['ACTION3','ACTION3']+['ACTION1','ACTION1'],'L6aa: route the east shuttle from (26,3) down, west, up to the (24,5) dock')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
drive.click((24,3),'L6aa: load the RED at (24,3) into the east shuttle at (24,5) (select)')
drive.click((24,5),'L6aa: land red in the shuttle')
off,pegs,sh=drive.cur(); print('   after load: off',off,'sh',sh,flush=True)
