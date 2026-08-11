import parse,sys
bs=parse.blocks()
i=int(sys.argv[1]) if len(sys.argv)>1 else -2
j=int(sys.argv[2]) if len(sys.argv)>2 else -1
h1,a=bs[i]; h2,b=bs[j]
print('A:',h1); print('B:',h2)
if len(a)!=len(b): print('row count differ',len(a),len(b))
ch=[]
for y in range(min(len(a),len(b))):
    for x in range(64):
        if a[y][x]!=b[y][x]: ch.append((x,y,a[y][x],b[y][x]))
print('changed cells:',len(ch))
# summarize by (from,to)
import collections
c=collections.Counter((f,t) for _,_,f,t in ch)
for k,v in c.items(): print(' ',k,v)
if len(ch)<=250:
    for x,y,f,t in ch: print(f'  ({x},{y}) {f}->{t}')
