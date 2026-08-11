# lf52 — Peg Solitaire

## Mechanics (confirmed L1)
- Board: panel of 4x4 tiles. Tile (i,j) occupies x=11+6i..14+6i, y=12+6j..15+6j.
  Center click point: (12+6i, 13+6j).  [L1 geometry; re-derive per level]
- Tile value 1 = hole present. 'e' green diamond inside = PEG. 'a' = off-board.
- ACTION1..4 do NOTHING (no-op). Only ACTION6 x,y (click) matters. ACTION7=undo, RESET.
- Row y=0 is an ACTION COUNTER bar: each action turns one cell 0->1 left to right.
  64 cells => possible hidden step limit around 64? watch it.
- Click a peg => gray (3) ring highlight around it + light-gray (2) ghost circles
  in all legal landing tiles.
- Click a ghost landing tile => jump: peg moves there, jumped-over peg removed.
- Goal (hypothesis): reduce to a single peg.

## L1
Pegs (i,j): (1,1)(2,1)(4,1)(5,2)(5,4). Board: rows j=0..2 cols 0..6; rows j=3..6 cols 4..6.
Solution: (1,1)->(3,1); (3,1)->(5,1); (5,1)->(5,3); (5,3)->(5,5).

## Tools
parse.py: load_states(), diff(). Use it; never print grids raw.

## L2 mechanics (big findings)
- GOAL = reduce to exactly ONE peg on the whole board (all panels together).
- Dead end (no legal jumps) => all remaining pegs turn light-gray (2) and a
  PURPLE (f) object appears bottom-left. That purple thing is a RESTART button:
  clicking it restores the level's initial state (action counter keeps going).
- Row y=0 counter = actions used in CURRENT level (resets each level). 64 cells.
- Clicking a peg that has NO legal jump does nothing at all (no highlight).
- ACTION1/2/3/4 = up/down/left/right MOVE THE YELLOW/ORANGE SHUTTLE BOX along
  the black pipe track, one lattice step (6px) per press. Off-track = no-op.
- Global tile lattice: tile (X,Y) occupies x=1+6X..4+6X, y=3+6Y..6+6Y.
  Box drawn as 4x4 orange fill + 1px yellow frame on its lattice cell.
- L2 layout: panel A tiles X=1..7,Y=1..3 ; panel B tiles X=7..8,Y=7..8.
  Track cells: (8,2),(9,2),(9,3),(9,4),(9,5),(8,5)..(2,5),(2,6),(2,7),(2,8),
  (3,8)..(6,8). Box starts at (5,5).
  Dock A = (8,2) right-adjacent to A(6,1)=X7Y2. Dock B = (6,8) left-adjacent to
  B(0,1)=X7Y8.

## L2 SOLVED (66 actions total; 53 in-level)
Route: A(1,1)->A(3,1); A(3,1)->A(5,1); shuttle (5,5)->(8,2) [R,R,R,R,U,U,U,L];
A(5,1) jumps over A(6,1) INTO the shuttle; shuttle drives to (6,8)
[R,D,D,D,L*7,D,D,D,R*4]; shuttle peg jumps over B(0,1) into B(1,1). 1 peg -> win.
=> The shuttle is a movable board cell: when docked next to a panel edge cell it
   is a normal peg-solitaire cell (can be jumped into / jumped from).

## CORE MECHANICS (confirmed through L3)
- GOAL: reduce the whole world to EXACTLY ONE peg.
- ACTION7 = UNDO (restores previous position, incl. after a losing move).
- GRAY pegs + PURPLE key object = the position is UNSOLVABLE (the game tells you!).
  Not "no moves left" - legal moves can still exist. Click the purple thing (or
  ACTION7) to recover. This is an ORACLE: any move that strands a peg is flagged.
- ACTION1/2/3/4 = up/down/left/right move ALL shuttles at once, one lattice step
  along their own track; a shuttle whose track has no such step stays put.
- THE WORLD IS LARGER THAN THE 64x64 VIEW. The camera scrolls (it follows a peg /
  a loaded shuttle as it nears the view edge). Re-read the board after any move
  that might scroll and re-locate the camera before computing click pixels.
- Shuttle docks: a track cell adjacent to a panel edge cell; the shuttle then acts
  as a normal board cell in line with that panel row/column.
- Bare track cells are NOT playable holes; only the shuttle cell is.

## Tooling
- board.py  : Board(grid(file)) -> .cells {(X,Y):PEG/HOLE/SHUTTLE/SPEG}, .track, .edges
- world3.py : world model + locate() camera offset + pix() world->screen pixel
- solve3.py : bitmask DFS peg-solitaire solver over an explicit cell/triple list
- L3 solved at action 127 (61 in-level actions).

## PURPLE WALLS (new in L4)
- A purple 4x4 block with a light-magenta 2x2 pattern = a PERMANENT JUMP PIVOT.
  You may jump *over* it exactly like a peg, but it is never removed and you can
  never land on it. They are the only way to cross gaps in many panels.
- A shuttle parked next to a wall can launch its peg over the wall into the panel,
  and a peg can jump over a wall INTO a parked shuttle.
- Two shuttles on different tracks, one above the other with a wall between them,
  can transfer a peg shuttle->wall->shuttle.
- The CAMERA follows a LOADED shuttle as it moves (empty shuttles / plain jumps do
  not scroll it). That is the only way to explore the off-screen world.
- Per-level action counter (row 0) reached 63 on L4 without any reset; limit
  unknown but 64 cells wide - keep levels under ~64 actions to be safe.

## L5 findings
- There is NO per-level action cap: L5 took 90 in-level actions with no reset.
  Row 0's bar just fills to 64 and then greys out. Explore freely.
- A shuttle can carry a PURPLE WALL instead of a peg (yellow frame + purple
  interior, no orange). That is a MOBILE PIVOT: park it between two panel cells
  two apart and a peg can jump over it from one panel to the next.
  A peg-carrying/empty shuttle is a MOBILE HOLE (you can land in it).
- Detect shuttles by the yellow 'b' ring around a lattice cell (>=12 'b' cells).
- Separate track networks may be bridged only by jumps through a shared panel;
  a shuttle cannot cross from one network to another.

## Workflow per level
1. `./act board > /tmp/cur.txt`; `python3 look.py` -> merge into world.json,
   print pegs/shuttles/map + pixel coords.
2. Plan jump chain (peg-solitaire with walls as permanent pivots).
3. Position shuttles (all shuttles move together on every direction press!).
4. Execute clicks; re-read board after any loaded-shuttle move (camera scrolls).

## RED PIECE (new in L6)
- A RED diamond (colour 8) is a MOBILE WALL: it jumps like a peg but NEVER
  captures the piece it jumps over, and it can never be captured itself.
  It does NOT count toward the "one peg" goal (only GREEN pegs do).
- Red + green leapfrog: red jumps over green, then green jumps over red, ... the
  pair walks along a row/column. That is the universal transport for a lone peg.
- A red can be jumped into an empty shuttle and carried (like a purple wall).
- Camera rule: the viewport centres on the CENTROID of all green pegs
  (shuttle-carried pegs included), clamped to world bounds. Moving a peg right
  scrolls right. Empty-shuttle moves do not scroll.
- L6 cleared at action 409 (129 in-level actions).

## BLUE PIECE (new in L8)
- BLUE diamonds are a SECOND mobile-wall type, identical in behaviour to RED:
  they jump without capturing, cannot be captured, don't count toward the goal.
  Two blues can leapfrog each other along a line, so a pair walks freely.
- Track networks can be DISCONNECTED components; a peg crosses between them by
  jumping out of a shuttle in one component, through a panel, into a shuttle of
  the other. Pattern: shuttle -> (pivot in panel) -> shuttle two cells beyond.
- Shuttles on one track cannot pass each other; plan their order carefully.
- L8 cleared at action 669.

## RUN COMPLETE — WIN 10/10 at action 840/2500
Level costs (in-level actions): L1 13, L2 53, L3 61, L4 63, L5 90, L6 129,
L7 153, L8 107, L9 117, L10 54.

### Final rule summary
The game is PEG SOLITAIRE on a scrolling world of black-bordered panels linked
by shuttle tracks.
- GOAL: reduce the world to exactly ONE GREEN peg.
- Green jumps a straight 2 cells over an adjacent occupied cell into an empty
  cell. Jumping over a GREEN captures it; jumping over anything else does not.
- PURPLE-framed square = fixed wall: permanent pivot, never captured/landed on.
- RED / BLUE diamonds = mobile walls: they jump like pegs, never capture and are
  never captured, and don't count for the goal. Two of them leapfrog each other
  to walk anywhere; a red+green pair does the same.
- SHUTTLES (yellow ring) ride black tracks. ACTION1-4 move ALL shuttles at once.
  An empty shuttle is a mobile HOLE (a landing square); one carrying a wall/red/
  blue is a mobile PIVOT; one carrying a peg is transport. Shuttles on the same
  track cannot pass each other -> shunting puzzles.
- ACTION6 x,y selects a peg (only if it has a legal move; a gray ring + light-gray
  ghosts show the landings) then clicks a ghost to jump. ACTION7 = UNDO.
- Gray pegs + a purple key object = the position is UNSOLVABLE; undo or click the
  key to restart. It is a free correctness oracle.
- The camera scrolls: it follows loaded shuttles / the peg centroid, clamped to
  world bounds. Off-screen regions exist; drive a LOADED shuttle to reveal them.
- No per-level action cap.
