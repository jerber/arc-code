import sys,re
def last_final(path='logs.txt'):
    txt=open(path).read()
    i=txt.rfind('[final]')
    if i<0:
        i=txt.rfind('[anim 1/1]')
        block=txt[i:].split('\n')[1:]
    else:
        block=txt[i:].split('\n')[1:]
    rows=[l for l in block if re.fullmatch(r'[0-9a-f]{64}',l)]
    return rows[:64]
def grid_cells(rows):
    # find cell blocks: 4x4 regions
    cells={}
    for y in range(64):
        for x in range(64):
            pass
    return cells
if __name__=='__main__':
    rows=last_final()
    for y,r in enumerate(rows):
        print('%2d %s'%(y,r))
