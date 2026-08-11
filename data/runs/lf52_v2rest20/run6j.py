import drive
for i,(a,m,l) in enumerate([((21,3),(20,3),(19,3)),((20,3),(19,3),(18,3))]):
    drive.click(a,'L6j: leapfrog the green back west (select)')
    drive.click(l,'L6j: land')
drive.click((18,3),'L6j: load the green (18,3) over pivot (18,4) into shuttle B at (18,5) (select)')
drive.click((18,5),'L6j: land in shuttle B')
off,pegs,sh=drive.cur(); print('both loaded? off',off,'pegs',sorted(pegs),'sh',sh)
drive.press(['ACTION3'],'L6j: press left once - if the camera stays at 80 it is held by the parked loaded shuttle B')
off,pegs,sh=drive.cur(); print('after left: off',off,'sh',sh)
