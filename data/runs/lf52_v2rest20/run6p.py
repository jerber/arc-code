import drive
drive.press(['ACTION2','ACTION2','ACTION2','ACTION2','ACTION3','ACTION3'],'L6p: drive the loaded east shuttle to the (24,7) dock next to the sealed east region')
off,pegs,sh=drive.cur(); print('   off',off,'sh',sh,flush=True)
drive.click((24,7),'L6p: click the peg in the east shuttle at (24,7) to see which landings the game highlights')
