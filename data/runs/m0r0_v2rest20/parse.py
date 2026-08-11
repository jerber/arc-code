#!/usr/bin/env python3
"""Parse logs.txt into a list of (header, grid) entries. Grid = list of strings."""
import sys, re

def load(path="logs.txt"):
    entries=[]
    cur=None
    grid=None
    mode=None
    for line in open(path):
        line=line.rstrip("\n")
        if line.startswith("action "):
            cur=line
        elif line.startswith("[board]") or line.startswith("[final]"):
            grid=[]
            mode="grid"
        elif line.startswith("[anim"):
            grid=None; mode=None
        elif mode=="grid":
            if re.fullmatch(r"[0-9a-f]{64}", line):
                grid.append(line)
                if len(grid)==64:
                    entries.append((cur,grid))
                    grid=None; mode=None
            elif line.strip()=="" :
                pass
            else:
                mode=None
    return entries

def diff(a,b):
    out=[]
    for y in range(64):
        for x in range(64):
            if a[y][x]!=b[y][x]:
                out.append((x,y,a[y][x],b[y][x]))
    return out

if __name__=="__main__":
    e=load()
    print("entries:",len(e))
    for h,_ in e[-3:]:
        print(h)
