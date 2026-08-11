# Game: peg solitaire on a 64x64 pixel board

## Mechanics (confirmed, level 1)
- Actions available: ACTION1-4 (do NOTHING), ACTION6:x,y (click), ACTION7 (undo?), RESET.
- Row y=0 is an action counter: pixel x=n-1 turns 0->1 after action n. Ignore it.
- Panels: white(0) interior with black(5) border + blue(9) drop shadow. Purely decorative.
- Tiles: 4x4 blocks, spacing 6 px, value 1 (=empty hole) or e/green (=peg).
  Grid coords: col c -> x0 = X0+6c, row r -> y0 = Y0+6r. Click center (x0+1,y0+1).
- Click a peg -> gray(3) ring drawn around it (selected) AND every legal landing
  cell gets light-gray(2) rounded corners (8 cells: corners of the 4x4).
- Click a highlighted landing -> jump executes: peg moves there, jumped peg removed.
- LEVEL CLEARS when exactly 1 peg remains (level 1: landed on (5,5), scored).
- Board region can be non-rectangular (L-shaped: two overlapping panels).

## Cost
Level 1: 13 actions (6 wasted on probes). Each jump = 2 clicks (select + land).

## Level 2 mechanics (confirmed)
- ACTION1/2/3/4 = move the ORANGE SHUTTLE BOX up/down/left/right along the black
  pipe track by exactly 6px (=1 grid cell) per press. It follows the pipe and
  turns corners (just press the direction of the next segment).
- The shuttle is a 4x4 cell (orange when empty) with a yellow frame. When its
  interior aligns with the tile lattice next to a panel's edge, it acts as a
  normal grid cell of that panel: pegs can jump INTO it and OUT of it.
- Load a peg in, drive the shuttle around, jump the peg out on the far side.
- Pipes attach to a panel at the pixel-row/col centre of a tile row/col, so the
  dock cell is exactly one lattice step outside the panel border.
- DEADLOCK (no legal jump anywhere) => all pegs turn gray(2) and shake, and a
  purple key/lollipop object rises from the bottom-left. CLICKING the purple
  object restarts the level (same as RESET, 1 action).
- Win = exactly 1 peg left (level 1 & 2 both).
- L2 solution: dock shuttle at (7,1); jumps (1,1)->(3,1)->(5,1)->shuttle;
  drive R1,D3,L7,D3,R4; jump shuttle-peg over (6,7) to (7,7). 

## CONFIRMED RULES (after level 3)
- WIN = exactly 1 peg left on the whole board (pegs inside shuttles count).
- The WORLD CAN BE LARGER THAN THE 64x64 VIEW. The camera pans (glides <=8 px per
  action) toward a focus, clamped to world bounds. Focus = the cell you last
  clicked, or the shuttles after an arrow press. World width for L3 was 88.
  => ALWAYS re-parse the board and recompute the camera offset before EVERY click.
- Row y=0 is a per-level action meter: one pixel per action since the level (re)start.
  RESET clears it; clicking the purple key restores the position but NOT the meter.
  Never observed what happens at 64 - keep attempts under ~60 actions.
- ACTION1/2/3/4 move ALL shuttles at once (each along its own track, blocked ones
  stay). Park a shuttle on a perpendicular segment to hold it still.
- ACTION7 = UNDO (undoes the last state-changing action).
- Shuttle docked next to a panel edge cell = an extra grid cell for jumps.
  Export: peg jumps over the edge cell into the empty shuttle.
  Import: shuttle's peg jumps over the edge cell into the cell beyond.
- A region with N pegs can be emptied only via exports (each export removes 2 from
  the region); internal jumps remove 1. Imports are net 0 for the region, -1 overall.
- Level 3: world 88x64, 3 regions (16/7/24 cells), 14 pegs, 2 shuttles, 13 jumps.
  Solved in 46 actions after mapping.

## TOOLING (in this dir)
- parse.py    blocks()/last() -> (header, 64 rows) per logged action
- level.py    parse one screen: tiles/pegs/shuttles/track in screen coords
- world.py    stitch several views into worldmap.txt (offset fit, dy=0)
- wparse.py   structural parse of worldmap.txt: cells, track, conn, tconn, docks
- state.py    current board -> (camera offset, pegs, shuttles) in WORLD coords
- solve3.py   DFS over (pegs, shuttle loads) for a 1-peg solution
- drive.py    click(world_cell)/press() with live camera-offset correction
- run3.py     the L3 plan, executed step by step with verification

## Level 4 (cleared, score 4) - new mechanics
- PURPLE LOCK objects (4x4 with keyhole, colours f/7/0/5) sit on lattice cells:
  they are PERMANENT JUMPABLE PIVOTS - a peg can jump over one and it is NOT
  consumed. That is how a lone peg travels and how pegs enter/leave shuttles.
- Two shuttles can transfer a peg to each other THROUGH a pivot between them
  (shuttle A -> over pivot -> shuttle B), e.g. L4 (9,10) -> pivot (9,11) -> (9,12).
- The camera follows the peg that last moved (in particular a LOADED shuttle).
  An empty shuttle does NOT pull the camera. Clicking does not pan the camera.
  => to explore a big world, load a peg into a shuttle and drive it around.
- L4 world was ~118 x ~106 px (20x18 cells). Solved with a 50-action plan.

## Pipeline for a new level (use this!)
1. `python3 nmap.py <firstblock> <lastblock>`   -> canvas.npy + offsets.json
2. `python3 wstruct.py <firstblock> <lastblock>` -> structure.json (+ ascii map)
3. `python3 nstate.py`                          -> camera offset, pegs, shuttles
4. `python3 -c "import planner;..."`            -> Dijkstra plan (presses+jumps)
5. write runN.py with the plan and run it (drive.py re-fits the camera per click)
Normalise shuttles first (press one direction ~6x) so their positions are known.

## IMPORTANT (learned in level 5)
- The row-0 action meter is HARMLESS: level 5's attempt ran to 87 actions (bar
  full at 64) with no reset and no penalty. Explore freely.
- Shuttles can carry a PIVOT as cargo ('V' in my maps): a movable pivot you can
  park anywhere on the track to create a jump. Reposition it repeatedly.
- Level 5 (world ~133x64, many small panels + long tracks) took 87 actions.
- Track adjacency hidden under a shuttle body: treat a gap containing yellow (b)
  as connected (fixed in wstruct.py).

## LEVEL 6 - detailed analysis (unsolved)
World ~168x64. Structure:
  west panel (cols 1-7, rows 2-9) 3 greens + 1 RED; dock (8,7)<->(7,7)
  row-7 track cols 8-18 with vertical branches at col 15 and col 18 (rows 5,6)
  pivots (15,4),(18,4) bridge row 3 <-> the branch docks (15,5),(18,5)
  row-3 corridor: cells cols 15..25 (green at (16,3)); pivot (24,4) -> track (24,5)
  east tracks: col 24 (rows 5,6,7), row 7 (cols 24,25,26), col 26 (rows 3..7); 1 shuttle
  col-27 panel: (27,3),(27,4)green,(27,5)   -- entry only from (25,3) over a LOADED
     shuttle at (26,3); (25,5) is a dead cell (unreachable)
  sealed region (23,5),(23,6)green,(23,7),(22,7),(21,7),(21,8)green,(21,9):
     the only usable dock jump is shuttle(24,7) over an OCCUPIED (23,7) -> (22,7)
Win needs 1 green; 7 greens => 6 consumptions; the traveller must be an ODD-column
green to enter the col-27 panel from (25,3).

THE BLOCKER - camera arithmetic:
- The camera only tracks a LOADED shuttle's horizontal movement, rigidly:
  camera = shuttle.x0 - lock, where lock is fixed when the peg is loaded
  (lock = x0 - camera_at_load). It is sticky when no loaded shuttle moves.
  Re-centering (lock:=28) happens when a peg is loaded while the shuttle sits at
  screen x >= ~48.
- Ferrying out of the west panel forces lock 28, so after unloading at (18,3) the
  camera is 108-28 = 80. One extra (15,5)->(18,5) cycle gives 98, but that cycle
  flips the cycling peg's column parity odd->even, and the entry green must stay ODD.
  With only 1 green + 1 red ferryable out of the west (verified exhaustively by
  planner: you cannot get a green in one shuttle, the red in the other AND leave a
  green behind), there is no spare peg to do the camera cycle.
- Clicking (25,3) needs camera >= 87; clicking (24,3) needs >= 84. Reachable camera
  values are == 2 (mod 6): 80 is attainable with the right parities, 92/98 only by
  sacrificing the odd green. Hence the entry jump is unreachable.
Conclusion: either a mechanic is still missing (some other way to pan the camera or
to enter the col-27 panel), or the level needs a peg-routing I could not find.

## FINAL STATE OF RUN
score 5/10, level 6 unsolved, 763/2500 actions used.
Levels cleared: 1 (13 actions), 2 (60), 3 (82), 4 (112), 5 (87).
Level 6: mapped completely (see above) but the entry jump into the col-27 panel
needs the camera at >=87 px while an ODD-column green and an EVEN-column ladder
(the red peg) are both in the row-3 corridor.  The camera is a rigid follower of a
loaded shuttle (camera = shuttle.x0 - lock, lock fixed at load time), and every
manoeuvre that raises it above 80 flips the carried peg's column parity, which
destroys the one odd green available - the west panel provably yields only one
green plus the red (planner-exhaustive).
Remaining ideas not yet tried: some other camera trigger (a re-centre rule I could
not reproduce reliably), or a peg route into the sealed/col-27 regions that does
not need (25,3).

## SESSION 2 (resumed) - CORRECTED MECHANICS  [2026-08-10/11]

### RED PEG (level 6 only) - confirmed from log diffs
A jump consumes the jumped piece ONLY if jumper and jumped are BOTH green.
Any jump involving the RED (as jumper or as jumped) consumes nothing.
=> the red is a reusable ladder; it can never be removed.
Win must therefore be "1 GREEN left" (7 greens, 6 consumptions available).

### CAMERA - correct model (derived from 434 logged actions, verified)
* Jumps NEVER scroll the camera.
* The camera translates by the horizontal displacement of ANY GREEN peg that
  rides a shuttle: cam += 6 per action in which a green-carrying shuttle moves
  one cell horizontally (all shuttles move together, so it is +/-6 per action).
* A shuttle carrying the RED does NOT move the camera. Empty shuttles do not.
* Exception: the FIRST green movement after a level start/RESET (cam==0) snaps
  the camera so that green sits at screen x=28 (observed 3x: +20 at (8,7)).
* clamp [0,104]  (world is 168 px = 28 cols wide; verified at the right edge).
* Pump trick: move two loaded greens WEST together (costs -6/action once) then
  EAST separately (+6/action each) => net gain. Two greens are needed to pump.
* Cell (c,3) is clickable iff  6c-63 <= cam <= 6c+3.
  (25,3) needs cam>=87; (27,3) needs cam>=99 -> only cam=104 works.

### LEVEL 6 MAP (verified from pixels)
cells  west (2..5,2..5)+(2..7,6..8)+(4,9); north (15..18,2); corridor (15..25,3)
       +(16,4),(17,4); east (27,3..5); sealed (23,5),(23,6),(23,7),(22,7),
       (21,7),(21,8),(21,9); lone (25,5)
pivots (15,4),(18,4),(24,4)      track  (8..18,7),(15,5),(15,6),(18,5),(18,6),
       (24,5),(24,6),(24,7),(25,7),(26,7),(26,6),(26,5),(26,4),(26,3)
shuttles X,Y on the west track; Z on the east track (starts (26,3)).
Row-2 cells and (16,4),(17,4) are UNREACHABLE (decoys).
West and east tracks are NOT connected (verified pixel-wise at row 7 x=111..123).

### WEST PANEL - exhaustively searched (west.py)
Only 12 reachable states; exactly ONE dock-ready state: 1 green at (6,7) + red
at (7,7).  The west therefore yields exactly 1 green + the red, consuming 2 of
its 3 greens.  Corridor then holds Ga(green), Gb(native green at (16,3)), R.

### CORRIDOR BFS (corr.py) - the blocker, precisely
Full BFS over (Ga,Gb,R positions, X,Y positions, cam) = 655440 states.
* cam=104 IS reachable (with both greens in shuttles).
* BUT "a green at (25,3) with the red at (24,3)" is reachable ONLY at cam 90/92,
  and only with the other green DEAD.
Reason: a green can only reach (17,3) by jumping from (15,3) over (16,3); the
only piece that can be at (16,3) is the native green Gb (consumed) - the red can
reach (16,3) only from (18,3) over an odd piece at (17,3), which is circular.
So the corridor consumption is forced and must be clicked at (15,3) => cam<=93.
After it, only one green remains, and a single green cannot pump the camera.
=> the entry jump (25,3)->over Z(26,3)->(27,3) needs cam=104: UNREACHABLE.

### WHAT THIS MEANS
Some mechanic is still missing.  Next probe (cheap): SELECT a peg and read the
highlighted legal landings from the board (light-gray 2 in the tile corners;
hl.py does this).  That is a free oracle for the jump rules - use it on the red
and on a green to find out whether diagonal / longer / sliding moves exist.

### SESSION OUTAGE
From ~action 788 the upstream game returned {"error":"SERVER_ERROR","message":
"game lf52-271a04aa not found"} for every ACTION/RESET; status and board still
answer from the broker cache. retry.sh loops the probe until it comes back.

### JUMP RULES - VERIFIED BY THE GAME'S OWN HIGHLIGHTS (offline oracle)
The board after a selection click shows the selected peg ringed in gray(3) and
every LEGAL LANDING outlined in light-gray(2).  109 such selections in the
level-6 log were checked against my model: 0 mismatches.
=> orthogonal jumps only, distance 2, over an occupied cell / pivot / loaded
   shuttle, landing on an empty cell or an EMPTY SHUTTLE.  No diagonals, no
   long jumps, no sliding.  (Row-2 and (16,4),(17,4) cells really are decoys.)

### CAMERA - final confirmation
Correlating every ACTION3/4 in level 6 with the cargo of the shuttles that
moved: green cargo -> cam +/-6 every time; RED-ONLY cargo -> cam unchanged
(6/6); empty -> unchanged.  ACTION7 = UNDO (it moved the camera in level 3 only
because it undid a shuttle move).

### IMPOSSIBILITY PROOF (within the verified model)
* A green can never reach a column >=17 while the other green is alive
  (BFS over 655440 states).  So the corridor consumption is forced, and it must
  be played as: green at (15,3) jumps over green at (16,3) -> (17,3).
* That click on (15,3) requires cam <= 93, i.e. cam <= 92.
* After it only ONE green remains; a single green cannot raise the camera
  (its rides must be net-zero to keep its odd parity), and the red never moves
  the camera.  So cam <= 92 for the rest of the level.
* The entry jump (25,3) -> over loaded Z(26,3) -> (27,3) needs to click (27,3),
  which needs cam >= 99.
=> level 6 is unwinnable unless a mechanic outside this model exists.
Untested candidates: ACTION5 (never used once in 788 actions), and camera
auto-scroll when a highlighted legal landing is off-screen.

### SESSION LOSS (critical, 2026-08-11)
The upstream ARC game vanished: every ACTION/RESET returns
  {"error":"SERVER_ERROR","message":"game lf52-271a04aa not found"}
`act status`/`act board` kept answering from the broker's cached state.json
until I ran `act init ... --again`, which cleared state.json and then failed on
the upstream RESET.  Now `act status` reports "no state.json".
Score at the time of the outage: 5/10, 788/2500 actions, level 6 attempt 1.
reinit.sh loops `act init lf52-271a04aa` every 20s until the upstream returns.
If it returns, the game restarts at level 1: replay.py replays the recorded
354-action solution for levels 1-5 (extracted from logs.txt), then plan_main.json
(90 actions, verified in sim.py) sets up level 6 at cam 92 with the traveller at
(25,3) and the red at (24,3) - the best position reachable under the verified
rules - and the remaining probes (ACTION5, camera-scroll-on-select) get tested
there.

### LEVEL-3 CAMERA (resolved): there IS a glide, but level 6 never lags
In level 3 an ACTION4 moved the shuttle 6 px east while the camera moved 8 px
(measured from the yellow shuttle frame: it slid 2 px left on screen).  So the
camera glides at <=8 px/action toward a target.  In level 6 the target never
gets more than 6 px ahead (it is the tracked green's shuttle), so the camera
appears to follow rigidly.  ACTION7 = UNDO (its +8 in level 3 was the undo of a
shuttle move).

### WHY LEVEL 6 CANNOT BE FINISHED (complete argument)
Reaching (27,3) needs cam=104.  cam only changes when a GREEN rides a shuttle.
The corridor has a hard parity structure:
 * a green unloaded at (15,3) is odd, at (18,3)/(24,3) even; jumps preserve
   column parity, so the traveller that must stand on (25,3) is odd and can only
   enter the corridor at (15,3);
 * the red is the only ladder; it ladders the opposite parity only, and flipping
   its parity requires it to reach (15,3), which requires a green helper on
   (16,3) that is then stuck there forever unless consumed;
 * therefore exactly one of the two greens is consumed in the corridor and the
   survivor's last shuttle ride must end at (15,3) - a click that needs cam<=93.
After that there is no green left to move the camera, so cam <= 92 < 99.
Verified by exhaustive BFS (655440 states) and by the game's own highlight
oracle.  The only untested lever left is ACTION5, which was never played once in
788 actions.

### STATE AT END OF THIS SESSION
No action was ever accepted this session: the upstream game was already gone
when I first tried to act (score 5/10, 788/2500 actions).  recover.sh is left
running: it retries `act init lf52-271a04aa` every 15s and, the moment the
upstream answers, runs master.py = ACTION5 probe + replay.py (the recorded
354-action solution for levels 1-5), restoring the score automatically.
Files worth keeping: sim.py (rules+camera simulator), corr.py (corridor BFS),
west.py (west-panel search), fastfit.py/exec6.py (live camera fit + executor),
plan_main.json (90-action level-6 setup, simulator-verified), replay15.json.
