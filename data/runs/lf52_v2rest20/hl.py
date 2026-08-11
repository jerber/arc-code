"""Read current board, report cells with highlight marks (value 2) and rings (3)."""
import subprocess,sys
def board():
    r=subprocess.run(['./act','board'],capture_output=True,text=True)
    rows=[l for l in r.stdout.splitlines() if len(l)==64 and all(c in '0123456789abcdef' for c in l)]
    return [[int(c,16) for c in row] for row in rows]
def report(cam):
    a=board()
    out=[]
    for c in range(cam//6-1,(cam+64)//6+1):
        x0=6*c-cam
        if x0<0 or x0+4>64: continue
        for r in range(0,11):
            y0=6*r
            if y0+4>64 or y0<1: continue
            v=[a[y0+dy][x0+dx] for dy in range(4) for dx in range(4)]
            corners=[a[y0][x0],a[y0][x0+3],a[y0+3][x0],a[y0+3][x0+3]]
            ring=[]
            if x0>=1 and y0>=1 and x0+4<64 and y0+4<64:
                ring=[a[y0-1][x] for x in range(x0-1,x0+5)]+[a[y0+4][x] for x in range(x0-1,x0+5)]+[a[y][x0-1] for y in range(y0-1,y0+5)]+[a[y][x0+4] for y in range(y0-1,y0+5)]
            tag=''
            if 2 in corners: tag+='HL'
            if 3 in ring: tag+=' RING'
            if 3 in v: tag+=' sel'
            if tag: out.append(((c,r),tag,''.join('%x'%x for x in corners)))
    return out
if __name__=='__main__':
    cam=int(sys.argv[1])
    for k,t,c in report(cam): print(k,t,c)
