# Game notes (tu93-0768757b)

## Rendering / geometry
- Board 64x64 hex digits. Row 63 = magenta bar = **remaining step budget**:
  remaining_px = round(64 * (1 - steps/50)). => **per-level step limit = 50**.
- Playfield is a 21x21 grid of 3x3 pixel **blocks**; block (i,j) covers
  x=3i..3i+2, y=3j..3j+2. Read center pixel (3i+1,3j+1).
- Maze: nodes on blocks 2 apart; between two nodes the intermediate block is
  '2' (light gray) if open, '5' (black=wall) if closed. Node blocks are '0'.
- One ACTION moves the player **2 blocks (1 node)**.

## Actions
Only ACTION1..4 + RESET. ACTION1=up ACTION2=down ACTION3=left ACTION4=right.
Confirmed. No ACTION5/6/7.

## Entities
- Player: 3x3 blue '9' block with a facing pixel ('4' off-black) on the side it
  faces.
- Goal: green 'e' block. Reaching it clears the level (+1 score).
- Red '8' block with colored facing pixel ('f' purple, later 'b' yellow):
  hostile. Level 2: sat at node (12,9) facing left; player walked (4,9)->(6,9)
  ->(8,9) with no reaction; when player stepped to (10,9) (1 node away) the red
  moved 1 node left onto the player => GAME_OVER. Hypotheses to test:
  (a) pounces when player within 1 node; (b) moves on a timer (it moved on
  level step 4).

## Levels
- L1: plain 11x11-block maze, 6x6 nodes, cleared in 18 actions.
- L2: nodes row j=9: i=4,6,8,10,12,14,16; goal (16,7); start (4,11);
  loop: (8,9)-(8,11)-(10,11)-(12,11)-(12,9)-(10,9)-(8,9). Red starts (12,9),
  the only corridor toward the goal.

## Red guard mechanic (CONFIRMED, L2)
- Red '8' block has a facing pixel (purple 'f') on one side = its **gaze**.
- It is static. It ignores the player everywhere except the single adjacent
  node in its gaze direction.
- Step into the node it faces  -> it moves onto you, GAME_OVER.
- Step INTO the red block itself from any non-gaze side -> red is destroyed,
  player takes its node. (L2 solved this way: approached from below, ACTION1.)
- => treat red as: "must be attacked from behind/side; never stand on the node
  in front of it".

## HUD bar (row 63) = per-level action budget
remaining_px = round(64*(1 - n/LIMIT)). LIMIT is per level:
L1=50, L2=50, L3=~35(1.83px/act), L4=20 (3.2px/act).
RESET restores the bar to 64 and consumes no bar (but costs 1 global action).
No-op moves (into a wall) DO burn the bar but do NOT tick the world.

## Guard taxonomy (confirmed)
- Red '8'  = STATIC gaze guard. Kills you if you stand on the one node it
  faces. Attack it by moving into it from any other side -> destroyed.
- Orange 'c' = PATROLLER. Moves 1 node per player action in a straight line,
  REVERSES when the next node is a wall (verified at (13,13) in L4, it did not
  turn into the open side corridor). Facing pixel = current travel direction.
  Kills you by moving onto your node. Presumably killable by moving into it
  from a non-facing side (never needed yet).
- Deaths are cheap: GAME_OVER just bumps `attempt`, keeps score, aborts the
  rest of the batch. Experiment freely; the scarce resource is the per-level
  bar, which RESET refills.

## Tooling
- game.py  : Board (auto-detects 3px grid offset from the player block),
             entities(), facing detection, dump().
- patrol.py: Lv() builds the node graph (parity from the player), traj()
             predicts a bouncing patroller, search() BFS over (pos,tick,reds)
             for a safe route. This solved L4.

## Maroon 'd' = HUNTER (confirmed L8)
- Sleeps on its post. Wakes when the player enters its **gaze line** (the
  facing direction) within 2 nodes. From the NEXT tick on it is a permanent
  BFS chaser: 1 node per player action, shortest path, turns corners.
- Its facing pixel while chasing = **the direction it will move next tick**.
  (Verified repeatedly - read it to resolve shortest-path ties.)
- Player/chaser distance parity is invariant once it is awake (always even).
- Contact = death, so it cannot be attacked; it must be lured off its post and
  looped around using a cycle in the maze. Being followed at gap 1-2 is safe:
  it steps into the node you just vacated.
- L8 solution: kill the red to open the 6-cycle, wake the hunter at its gaze
  node's neighbour, lead it into the cycle, go round so it is on the far arc,
  then dash up the corridor it vacated.

## L9 (final level) — solved, run WON 9/9 in 244 actions
Layout: 33 nodes, bipartite (all cycles even) so player/guard **parity is a hard
invariant**: an entity that shares the player's phase can collide with it but can
never swap with it, and the player can never step into its just-vacated node.
Guards: 1 hunter (9,7) blocking the only exit from the start dead-end, 3
patrollers, 2 reds guarding the goal in a chain ((9,15) gazes at (9,13), (9,13)
gazes at the goal (11,13)) so they must be killed bottom-up from (11,15).

Facts established here:
- An awake hunter stays at *exactly* graph distance 2 (its step always reduces
  distance by 1, ours increases it by 1) => it can never be shaken off by speed,
  and being followed is harmless; only turning back into it kills you.
- Hunter step rule: among distance-minimising neighbours it prefers to continue
  STRAIGHT, else turn, and its facing pixel shows the move it will make next
  tick - a perfect 1-step oracle, worth reading before every commitment.
- Hunters and patrollers pass through each other (verified at (9,5)): no kill,
  they just overlap and only one is drawn (so an entity can hide another).
- Patrollers can never be attacked (they are never stationary).
- The win: patroller timing on column 15 forbids a straight descent, so the
  route detours through the 4-cycle (15,7)-(17,7)-(17,9)-(15,9); at the moment
  that should have been fatal the column patroller was sitting on (15,7) with
  the hunter, and the hunter stepped to (17,7) instead of onto the player -
  i.e. a patroller sharing a node with a hunter perturbs its chase.
