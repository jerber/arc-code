import drive
drive.click((24,5),'L6ab: unload the RED from the shuttle at (24,5) over pivot (24,4) -> (24,3) (select)')
drive.click((24,3),'L6ab: land red at (24,3) - watch whether the camera pans east')
off,pegs,sh=drive.cur(); print('   off',off,'pegs',sorted(pegs),'sh',sh,flush=True)
