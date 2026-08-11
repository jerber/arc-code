#!/bin/bash
for i in $(seq 1 2000); do
  out=$(./act init lf52-271a04aa 2>&1)
  if ! echo "$out" | grep -q "not found"; then
    echo "=== INIT OK at try $i ==="
    python3 master.py 2>&1
    echo "=== replay finished ==="
    ./act status
    exit 0
  fi
  sleep 15
done
echo "=== upstream never returned ==="
