You are playing a grid puzzle game you have never seen before: a sequence of
levels on a 64x64 board of colored cells. Coordinates are `x,y`, both 0-63.

`./act do ACTION1 ACTION6:30,40 ...` plays actions in order. `./act status`
prints where you are and what this game accepts; `./act board` prints the
current board. Boards are printed as hex digits, one cell each — the digit is
the cell's value, and the color legend is at the top of `logs.txt`.

Actions are game-specific. Conventionally ACTION1-4 move up/down/left/right,
ACTION5 interacts, ACTION6 clicks at `x,y`, ACTION7 undoes, RESET restarts the
level — but verify rather than assume.

The brief above says what this environment is. Nobody will explain its rules;
you discover them by acting and reading what happened.

Clear every level: that is what you are here for. Spend as few actions as you
can along the way, but treat that as a distant second — a level you never clear
scores nothing and ends the run there, while running well past a sensible action
count on one you *do* clear costs only a little. When the two pull against each
other, finish the level.

## Acting

`./act do` plays a batch of actions in order and **stops as soon as one changes
the score**, discarding the rest — a score increase means a level was cleared,
so the state you planned against is gone. Pass `--plan "..."` with each batch;
it is recorded in the log beside those actions and becomes your briefing
history.

Every action counts against the budget, including RESET. act refuses anything
invalid and tells you why — read the error, it is information about the
environment.

## Memory

`logs.txt` holds the whole run: an entry per action with your plan, the action,
and the state it produced. It is written for you, verbatim, and it is the only
complete record — your context is not. Its format and legend are documented in
its opening lines; read them before anything else.

**Read it with code, not with your eyes.** Use grep, sed and Python on the
states it records: a large grid taken in by eye from your context comes with
transcription errors, and those send you chasing phantoms. Diffing two states
to see exactly what changed is the single most useful thing you can do.

Never print the log, or a whole state, into your own context. The log grows to
hundreds of thousands of lines, and a grid you have read by eye is a grid you
may have read wrong. Orient with `wc -l`, then `grep -n` for the headers you
want and `sed -n 'a,bp'` for the range you need; pipe states into a script and
print the conclusion, not the grid.

Keep durable findings in `notes.md`: confirmed mechanics, level solutions,
hypotheses you have ruled out. Your context may compact; files survive.
Helper scripts you write are worth keeping too — a parser or a simulator you
can re-run beats re-deriving it.

## Playing well

- Guess how something works, then spend **1-2 actions** checking the guess and
  diff what changed. Once you have a mechanic nailed down, send **10-20
  actions** in one batch rather than paying for a round trip each.
- Break the state into distinct objects — position, appearance, size and
  behavior are the evidence — and give each one a role: the thing you steer,
  the things that block it, the thing that ends the level, a counter,
  decoration.
- Expect hidden limits. Many environments reset a level once too many steps
  have gone by.
- If a level has cost several times what the levels before it did and you still
  cannot say what ends it, your model is probably *wrong* rather than
  incomplete, and a wider search inside a wrong frame finds nothing. Say so in
  `notes.md` with what you have ruled out, then re-derive what the things in
  front of you *are*, as if you had just arrived.
- Shell and Python loops around `./act` are encouraged — branch on a parsed
  state, repeat until something changes, search for a coordinate. You are not
  limited to fixed action lists.
- Before committing a long sequence, simulate it against your model of the
  rules and say what you expect; then check the log against that expectation.

Play until `./act status` reports you have won or the budget is spent. Do not
stop to ask questions — there is nobody to answer them.
