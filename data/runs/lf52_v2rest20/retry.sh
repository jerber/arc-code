#!/bin/bash
# retry the red-selection probe until the game session comes back
for i in $(seq 1 200); do
  out=$(./act do --plan "L6 probe: select RED at (18,3) to read highlighted legal landings" ACTION6:47,19 2>&1)
  if ! echo "$out" | grep -q "not found"; then
    echo "SUCCESS at try $i"; echo "$out" | head -5; exit 0
  fi
  sleep 30
done
echo "STILL DOWN after 200 tries"
