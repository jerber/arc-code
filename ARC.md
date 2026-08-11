You are playing a grid puzzle game you have never seen before: a sequence of
levels on a 64x64 board of colored cells. Coordinates are `x,y`, both 0-63.

`./act do ACTION1 ACTION6:30,40 ...` plays actions in order. `./act status`
prints where you are and what this game accepts; `./act board` prints the
current board. Boards are printed as hex digits, one cell each — the digit is
the cell's value, and the color legend is at the top of `logs.txt`.

Actions are game-specific. Conventionally ACTION1-4 move up/down/left/right,
ACTION5 interacts, ACTION6 clicks at `x,y`, ACTION7 undoes, RESET restarts the
level — but verify rather than assume.
