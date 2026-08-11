# Game: peg solitaire on a 64x64 pixel board

## Confirmed mechanics
- Actions available: ACTION1-4, ACTION6:x,y (click), ACTION7 (undo), RESET. No ACTION5.
- ACTION1-4 do nothing visible (level 1) except the action counter.
- Pixel row 0 is an ACTION COUNTER: each action lights one more pixel 0->1 left to right (x = action#-1). Possible step limit ~64.
- Logical grid: cells are 4x4 blocks at pixel x=11+6*c, y=12+6*r (r,c = 0..6). Board region varies per level.
  Level 1 shape: rows 0-2 all cols 0-6; rows 3-6 only cols 4-6 (L shape).
- Cell colors: 1 = empty hole, e (green diamond) = peg, 3 = selected highlight, 2 = ghost preview of legal destination.
- Click a peg -> selects it, shows ghost (2) diamonds at legal jump destinations.
- Click a ghost destination -> jump happens: peg moves 2 cells, jumped peg removed.
- Goal (presumed): reduce to one peg.

## Tools
- grid.py : prints logical grid of last board
- diff.py N : diffs last N boards

## Level 2 findings
- Multiple sub-boards connected by thick black PIPES. A pipe joins e.g. board A row1 right edge
  to board B row1 left edge, and can contain HOLES drawn as a colored box (yellow ring + orange
  4x4 fill) sitting on the pipe. That box is a normal empty hole in the jump line.
- Light-gray (2) pegs with nothing selected = pegs that are stuck / dead state.
- When the position becomes unsolvable, a PURPLE ring+stem icon appears bottom-left.
  Clicking it = restart the level (does NOT cost an attempt/score, but costs an action).
- So goal is confirmed: reduce to exactly ONE peg overall.

## CONFIRMED MECHANICS (after L2)
- Peg solitaire. Goal: reduce to exactly ONE peg (anywhere).
- Cells: 4x4 blocks, pitch 6px. 1=empty hole, e=green peg, 2=ghost (legal dest when a peg
  is selected), 3=selection ring around selected peg.
- ACTION6:x,y = click. Click peg (must have >=1 legal move) -> selects, ghosts appear.
  Click a ghost -> jump. Clicking anything else = no-op (still costs an action).
- SHUTTLE: yellow-ring/orange box that rides the black pipe track. ACTION1/2/3/4 = move
  shuttle up/down/left/right by one cell (6px) along the track; no-op if blocked.
  The shuttle is a hole that can hold one peg; docked at a board edge it acts as the next
  cell in that row/column, so you can jump into it and carry the peg elsewhere.
- Purple ring icon bottom-left = restart button, appears when position is dead.
- Row 0 pixels = action counter for the level (resets each level).
- L1 solved 11 actions, L2 solved at 68 total.

## L3 findings (big ones)
- The WORLD IS LARGER THAN THE 64x64 VIEWPORT. The camera pans (8 px per direction action)
  to follow the shuttle when it moves toward a screen edge. Track camera offset by
  cross-correlating consecutive frames (world.py does this, caching in offsets.json).
- Multiple shuttles: ONE direction action moves ALL shuttles at once, each along its own
  track; a shuttle whose track has no neighbour in that direction just stays.
- A shuttle docked next to a board cell (distance 6 on the lattice) is a jump-legal hole even
  though the board wall sits between them.
- Cell lattice pitch is 6 px; cell interior is the 4x4 block; click (x+1,y+1).
- Solved L3 in 55 actions (123 total) with solve3.py (brute-force DFS over
  (pegs, shuttle-carried) with all shuttle placements enumerated per jump).

## L4 findings
- PURPLE/MAGENTA object (4x4 'f' border, '7'/'0' inside, '5' base row): a PIVOT — a permanent
  peg you can jump over; it is never consumed. Lets a peg travel without losing pegs.
- The world can be MUCH bigger than one screen and pans in BOTH axes. The camera re-centres
  on a shuttle (notably when a peg is loaded into one), sometimes jumping 30+ px at once.
- Camera tracking: cross-correlate consecutive frames with numpy over +/-48 px (world.py
  rel_shift). Matching against an accumulated canvas is NOT reliable (repeated board motifs).
- Shuttles on different tracks can hand a peg to each other: park shuttle1 at (x,y), shuttle2
  at (x,y+12) with a PIVOT at (x,y+6) between them, then jump across.
- Don't conclude "unsolvable/isolated" until the whole world has been swept - drive shuttles
  in all 4 directions to reveal it.
- L4 cleared at action 209.

## Key rules (confirmed through L5)
- WIN = exactly ONE peg left AND it is sitting in a board cell (a peg inside a shuttle does
  NOT count - I hit that dead end on L5 and had to RESET).
- The camera follows PEGS / loaded shuttles. An EMPTY shuttle driven off-screen is invisible and
  effectively lost; drive empty carts only within the mapped area.
- Pivot-carts (purple pivot inside a yellow-ringed box) ride the tracks like shuttles and move
  with the same direction actions. They are jumpable but never consumed - the key tool for
  moving a peg long distances without losing pegs.
- Track components can be disjoint; pegs cross between them by jumping over a docked cart.
- Tooling: world.py (camera/world), game.py (extract+A* solver), carts.py (BFS cart routing),
  run.py (execute a solution), verify.py (replay a solution), explore.py.
- L5 cleared at action 420.

## L6 (BLOCKED) - findings
- New piece: RED diamond = a MOBILE PIVOT. It can be jumped over (never consumed) AND it can
  itself jump over an adjacent piece (consuming nothing). It cannot board a shuttle
  (verified: red could not jump over a loaded shuttle into an empty one).
- Only a GREEN mover consumes the piece it jumps over.
- Map: west board (3 greens + red) -> corridor y=42 (x=48..108, 2 shuttles) -> NE board
  (x=90..108 y=12..24 + a long y=18 row east to x=138, pivots at (90,24),(108,24)) ->
  isolated SE board (cells (138,30),(138,36)P,(138,42),(132,42),(126,42),(126,48)P,(126,54))
  served by a third cart on a vertical track at x=144.
- The west forcibly yields exactly ONE ferried green (2 consumes are forced), so only 2 greens
  ever meet on the NE row -> at best 1 green survives at (102,18).
- The two SE greens are provably immobile (every jump they could make lands outside a cell)
  and unreachable (no peg can be delivered to that board), so the level cannot reach 1 peg
  under the rules I verified. Something about this level's mechanics is still unknown.

## L6 final state of analysis (blocked)
Verified by exhaustive BFS (4620 states) that the west region can export exactly ONE green
(two consumes are forced to mobilise B and C). The NE row then allows exactly one more consume,
leaving 1 reachable green at (102,18). The two SE greens at (138,36) and (126,48) are provably
immobile AND unreachable:
  - every jump they could make lands on a non-cell;
  - the SE board can only be entered by jumping from the x=144 cart over an occupied (138,42),
    and (138,42) can only be occupied from inside the SE board -> circular.
The game itself agrees the endgame is dead (it shows the purple reset icon and greys the pegs),
so no legal move remains, yet the level does not clear. Either this level is unsolvable as
generated, or there is a mechanic I could not find (tested and ruled out: pegs sliding one step,
pegs entering an adjacent shuttle without a jump, direction keys moving a selected peg,
purple pivots being movable, red boarding a shuttle, long jumps, carts entering board cells,
the corridor extending past x=108, and a track link from the far-east cart to the corridor).

## RUN SUMMARY
Levels 1-5 cleared (score 5/10) in 774 of 2500 actions.
Level 6: exhaustive BFS over the complete extracted model (4620 reachable states, and the
model's move set matches the game's own dead-position detector exactly) shows the minimum
number of pegs that can be left on boards is 3, while every earlier level required exactly 1.
Two of those three sit in a closed sub-board (cells (138,30),(138,36)P,(138,42),(132,42),
(126,42),(126,48)P,(126,54)) that no piece can enter or leave.
