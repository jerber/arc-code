import drive
drive.press(['ACTION2','ACTION3','ACTION3','ACTION1','ACTION1'],'L6z: bring the east shuttle to the (24,5) dock')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
drive.click((24,3),'L6z: load the RED at (24,3) into the east shuttle (screen x ~58, hoping the camera re-centres) (select)')
drive.click((24,5),'L6z: land red in the shuttle')
off,pegs,sh=drive.cur(); print('   after load: off',off,'sh',sh,flush=True)
