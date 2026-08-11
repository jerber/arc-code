import drive
drive.click((24,3),'L6o: load the green at (24,3) down over pivot (24,4) into the east shuttle at (24,5) (select)')
drive.click((24,5),'L6o: land in east shuttle')
off,pegs,sh=drive.cur(); print('   loaded: off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
drive.press(['ACTION2','ACTION2','ACTION4','ACTION4','ACTION1','ACTION1','ACTION1','ACTION1'],'L6o: drive the loaded east shuttle around its track (down, east, up) to pan the camera further east')
off,pegs,sh=drive.cur(); print('   after drive: off',off,'sh',sh,flush=True)
