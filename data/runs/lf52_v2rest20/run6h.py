import drive
drive.press(['ACTION3','ACTION3','ACTION1','ACTION1'],'L6h: bring a shuttle to the (15,5) dock')
drive.click((15,3),'L6h: load green (15,3) over pivot (15,4) into shuttle (15,5) (select)')
drive.click((15,5),'L6h: land in shuttle')
off,pegs,sh=drive.cur(); print('after load: off',off,'sh',sh)
drive.press(['ACTION2','ACTION2','ACTION4','ACTION4'],'L6h: drive the loaded shuttle east to pan the camera')
off,pegs,sh=drive.cur(); print('after drive: off',off,'pegs',sorted(pegs),'sh',sh)
