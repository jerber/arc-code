#!/bin/bash
for i in $(seq 1 600); do
  out=$(./act init lf52-271a04aa 2>&1)
  if ! echo "$out" | grep -q "not found"; then echo "INIT OK at try $i"; echo "$out" | head -5; exit 0; fi
  sleep 20
done
echo STILL DOWN
