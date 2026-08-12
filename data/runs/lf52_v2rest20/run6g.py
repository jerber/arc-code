import drive
drive.press(['ACTION1','ACTION1'],'L6g: raise the loaded shuttle to the (18,5) dock')
drive.click((18,5),'L6g: unload green over pivot (18,4) -> (18,3) (select)')
drive.click((18,3),'L6g: land at (18,3) - should pan the camera east')
off,pegs,sh=drive.cur(); print('after off',off,'pegs',sorted(pegs),'sh',sh)
