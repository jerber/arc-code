# Game notes

## Actions
ACTION1..4 = move up/down/left/right (3 cells per press). ACTION5 = switch which
cross is "active". RESET. No ACTION6/7 (no click, no undo). Budget 2500 actions.

## Objects (level 1)
- Two plus/cross shapes, one yellow (b, arm radius 11), one blue (9, radius 13).
  The ACTIVE one has a WHITE (0) center cell. ACTION5 toggles active cross.
- 3x3 boxes: off-black (4) frame with a colored center (b or c...). 4 yellow-centered,
  4 blue-centered.
- Row 63 = purple (f) bar; fills from the RIGHT with off-white (1), one cell per
  MOVE action (ACTION5 does not count). Likely a 64-move limit per level.

## Goal hypothesis (level 1)
For each color: the 4 boxes of that color lie on a plus pattern — two share an x,
two share a y. Their intersection is the target center; centering the cross there
makes its 4 arms cover all 4 box centers.
  yellow boxes (15,3),(6,9),(24,9),(15,17) -> center (15,9)
  blue boxes (48,16),(40,24),(53,24),(48,35) -> center (48,24)
Movement is 3/step so targets are reachable only if deltas divisible by 3.

## Tools
parse.py — load()/final_grid()/objects()/describe()/diff() over logs.txt.

## CONFIRMED RULES (after L1, L2)
- Shapes come in families: plus (4 arms, r), X (4 diagonals, r), diamond RING
  (|dx|+|dy|==r), possibly square ring. Shape has a centre cell (white 0 when
  that shape is ACTIVE; can be hidden if another shape draws over it).
- ACTION5 cycles the active shape (order seen L2: orange -> maroon -> blue -> ...).
- ACTION1/2/3/4 = up/down/left/right, 3 cells per press, active shape only.
- WIN CONDITION: for every colour, translate that shape so that EVERY box of the
  same colour lies on a cell of the shape. Level clears when all colours satisfied.
- Reachability: only translations by multiples of 3.
- Row 63 bar = round(actions_this_level * 64/100): implies ~100 action limit per
  level attempt. Watch it.
- Shapes clip at board edges without harm; shapes may overlap/draw over each other
  (later-drawn colour hides cells) -> shape fitting must tolerate missing cells.
- L1 solved in 21 actions, L2 in 50.

## L3: several shapes can share one colour; all boxes must be covered by SOME shape
(set-cover over translations). L3 shapes: X r11, diamond ring r12, hline r21.

## L4: PALETTE / RECOLOURING
6 swatches = 4x4 solid colour blocks with a light-gray (2) border, at fixed spots
(x 5-8/29-32/53-56, y 5-8/55-58). If any cell of the active shape overlaps a
swatch's 4x4 block, the WHOLE shape takes that colour immediately.
Win needs shape colour == box colour AND geometric coverage.
Beware: dragging a shape across the board can brush another swatch and repaint it —
plan paths that avoid swatches.
Scores: L1 21 actions, L2 50, L3 47, L4 68.

## L6: OBSTACLES + DEFORMATION (big one)
An off-white ('1') block (8x8 with a round hole) is a fixed OBSTACLE. A move
applies to every PART of the active shape; a part whose destination cells would
overlap obstacle cells does NOT move while the others do. Consequences:
 - A "plus" is really an hline + a vline part: they can be DESYNCED into an
   offset cross (each keeps its length). Verified model in deform.py:
   part moves iff onboard(cells(dest)) & obstacles == empty.
 - A square ring is a RECTANGLE with a conserved size budget: width+height = const
   (L1 square 19+19=38). Blocking one side shifts the opposite side => that
   dimension shrinks by 3 and the perpendicular one grows by 3 (symmetrically,
   alternating ends). Sides stay on the same mod-3 lattice.
   L6 answer: 4 yellow boxes were the CORNERS of a 10x28 rectangle (10+28=38).
 - Off-board parts/sides persist and cannot be blocked (obstacles are on-board),
   so parking a side off-board is a legitimate manoeuvre.
Scores: L5 63 actions, L6 75.

## L7 (cleared, 126 actions): 3 shapes, 5 3x3 swatches at y=3..5, same '1' obstacle.
Assignment was forced by which shape could span which box set. Technique that works:
 1. identify parts (hline/vline/rect sides) and the exact target part positions,
 2. desync with the obstacle (park the non-blocking part's span/row out of the
    obstacle's rows/cols so only the intended part is blocked),
 3. touch the right swatch LAST (check every part for stray swatch overlap; move
    the part's span off rows 3..5 before travelling sideways),
 4. translate rigidly on a clean path.
sim.py simulate(parts,state,colour,actions,obst,sw) reproduces the game exactly
for line-part shapes; rectangles need the budget rule (hand-planned).

## L8 (cleared) — full rule set, final
Two 13x13 rectangle rings, two sets of 4 boxes that are the CORNERS of a
rectangle with the same size budget (w+h=26): 'b' 7x19 at (9,39)-(15,57),
'6' 16x10 at (6,45)-(21,54). 13 swatches incl. a full-width band at y=29..31,
two 5x5 obstacles (top-right y=1..5, bottom y=55..59).

RECTANGLE RULES (verified):
 - Move: translate unless the translated ring overlaps an obstacle cell; then
   SQUEEZE — the leading edge stays, the trailing edge advances, that dimension
   -3 and the perpendicular +3.
 - Perpendicular growth alternates ends; first vertical growth extends BOTTOM,
   first horizontal growth extends LEFT.
 - No dimension below 4; a move that would need a smaller one is REFUSED.
 - A move whose resulting CENTRE would leave the board is REFUSED (no movement).
 - RECOLOUR triggers on adjacency: shape cell inside the swatch block OR its
   1-cell '2' border. Touching two swatches at once gives an unstable result —
   never plan through it.
 - Crossing the y=29..31 swatch band needs the ring narrow enough that its
   hlines' on-board span fits a colour-free gap (w=4 at x=54..57, 45..48, 36..39,
   15..18) — hence: recolour wide above the band, squeeze to w=4 on the top
   obstacle, cross, grow back on the bottom obstacle, then position.

Tools: rect3.py (model+BFS), plan8.py (plan to next squeeze), drive8b.py
(observe board -> plan -> execute leg, with stuck-detection).
FINAL: WIN 8/8 in 804 actions.
