import parse,sys
hdr,rows=parse.last()
y0,y1,x0,x1=[int(v) for v in sys.argv[1:5]] if len(sys.argv)>4 else (0,63,0,63)
print(hdr)
print('    '+''.join(str(x%10) for x in range(x0,x1+1)))
for y in range(y0,y1+1):
    print('%3d '%y + rows[y][x0:x1+1])
