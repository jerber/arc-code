# Game notes (m0r0-492f87ba)

## Confirmed mechanics (level 1)
- Board 64x64 fine cells; the puzzle lives on a coarse grid of **5x5 blocks**.
  Level 1 origin (9,9), 9 cols x 10 rows.
- Two light-blue (`a`) 5x5 avatars, one in the yellow (`b`) left region, one in
  the orange (`c`) right region. Black (`5`) = floor/open, `b`/`c` = wall.
- ACTION1 = up, ACTION2 = down (assumed), ACTION3/ACTION4 = horizontal.
  **Horizontal input is MIRRORED between the two avatars**: ACTION4 moves the
  left avatar +x and the right avatar -x; ACTION3 the reverse. Vertical is the
  same for both.
- A blocked avatar stays put while the other still moves -> they desync.
- **Goal: get both avatars onto the SAME cell** (the mirror-axis column, col 4
  in L1, is where they can coincide). Merging clears the level.
- The two half-mazes are near-mirror-images but differ in a few cells; that is
  what makes the puzzle non-trivial.

## Tools
- `parse.py` : load logs.txt -> list of (header, 64-row grid); `diff(a,b)`
- `grid.py`  : coarse(g, ox, oy, nx, ny, w) -> block grid (majority colour)
- `solve2.py`: BFS over (posL,posR) with mirrored horizontal; goal posL==posR

## Level log
- L1: cleared in 18 actions (incl. 4 probes). Path found by BFS.

## Confirmed mechanics (level 3)
- **Blue (`9`) 2x2 dots** inside a floor block are MOVABLE BLOCKS / gates.
  They block avatar movement.
  - `ACTION6:x,y` on a dot SELECTS it: dot turns Yellow (`b`), both avatars turn
    Off-White (`1`) and freeze. Only one dot selected at a time.
  - While a dot is selected, ACTION1-4 push the selected dot one cell.
    **Dot movement is NOT mirrored** — ACTION4 = +x, ACTION3 = -x always.
  - `ACTION6` on any non-dot cell deselects and re-activates the avatars.
  - ACTION5 appears to be a pure no-op.
- Border rows 0/63 hold a white progress bar (~1 pixel per 2 actions in the
  level); it resets on level change. Possible step limit, never hit so far.
- L2's red/black checkerboard blocks were LETHAL (level reset on entry).

## Level log
- L1 cleared @18 actions. L2 cleared @53. L3 cleared @124.

## Key structural insight (level 4)
If the left maze and the mirrored right maze are IDENTICAL and the avatars start
at the same mirrored column, their dynamics are identical forever: the row
offset can never change and they can never merge. The movable dot must be
pushed to an ASYMMETRIC cell to break the symmetry. `solve4.py` does a full BFS
over (avatarL, avatarR, dot, mode) including the select-click, which handles
this automatically.
- L4 cleared in 11 actions (9x9 grid, blocks of 5, origin (9,9)).

## Confirmed mechanics (level 5)
- Full-block solid colours are terrain: a lone coloured block is a PRESSURE
  PLATE, a run of same-coloured blocks is a DOOR. The doors of colour X are
  passable ONLY while an avatar is standing on a plate of colour X.
- Trick: park an avatar on a plate in a spot where the needed direction is
  blocked by a wall/board edge, so repeating that action moves only the other
  avatar through the door.
- **The horizontal mirror sign can FLIP between levels.** In L1-L4 ACTION4 moved
  the left avatar +x; in L5 ACTION4 moved it -x. Always verify with one probe.
- L5 cleared @190 actions (15x13 grid, blocks of 4, origin (2,6)).

## Confirmed mechanics (level 6) — RUN COMPLETE, WIN 6/6 @230 actions
- Avatars frozen by a dot selection STILL hold down pressure plates, and the
  selected dot can be pushed through a door that those plates hold open. That is
  the only way L6 is solvable (verified by exhaustive search over the assumption
  variants: it is unsolvable if either is false).
- An avatar may stand on a door cell that then shuts, and can still walk OFF it —
  the passability test applies only to the cell being entered.
- Checkerboard hazards KILL rather than block, so they cannot be used as pins.
  Usable pins are: walls, board edges, SHUT doors, and the movable dot.

## Full mechanic summary
Two light-blue avatars, one per half. Vertical input moves both the same way;
horizontal input is mirrored (sign convention varies per level — probe it).
A blocked avatar stands still while the other moves: that is the only way to
desync them. Goal every level: land both avatars on the SAME cell.
Terrain: black floor; solid background colour = wall; red/black checkerboard =
lethal; lone solid colour block = pressure plate; a run of them = door of that
colour, open only while a plate of that colour is held; small inset blue square
= movable block (ACTION6 to select, ACTION1-4 to push, non-mirrored).
If the two half-mazes are exact mirrors and the avatars start mirror-aligned,
they can never merge — the movable block must be placed asymmetrically.

## Final score
score=6/6 state=WIN actions=230/2500
