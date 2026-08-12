# How Opus 5 loses at ARC-AGI-3

I ran Claude Opus 5 through this harness 191 times on the 25 public
ARC-AGI-3 games. It won 177 sessions and did not win 14. The clearest repeated
pattern in those 14 was early surrender: six sessions decided the current
level was impossible and stopped with 1,391–2,218 of their 2,500 moves unused.

In five of the six, the model had already recorded an unresolved question but
did not run the corresponding experiment. It marked its model as incomplete,
but did not reliably turn that uncertainty into targeted exploration.

This is the longer version of [when uncertainty does not lead to
action](../README.md#when-uncertainty-does-not-lead-to-action). The numbers come
from the run database, and everything in quotes is the model's own writing.
Three of the sessions below are published in full under
[`data/runs/`](../data/runs).

Each ARC-AGI-3 game is an unexplained video game drawn on a 64×64 grid. The
agent has to discover the controls, rules, and goal by acting. It gets at most
seven inputs and a budget of 2,500 actions, which I call moves below. It can
write any code it wants and keeps durable findings in `notes.md`.

Here is how the 14 non-wins ended:

| how the run ended | runs | moves it still had |
|---|---:|---:|
| used the whole budget | 4 | 0–39 |
| **decided the level was impossible and quit** | **6** | **1,391–2,218** |
| my infrastructure cut it off while it was still working | 2 | 723–2,330 |
| the ARC server deleted the game mid-run | 1 | 1,712 |
| ran out of conversation memory | 1 | 1,734 |

## Early exits

The six agents that quit left a median of about 2,000 moves unused, or 80% of
the budget. The last instruction in [`PROMPT.md`](../PROMPT.md) is: *"Play
until `./act status` reports you have won or the budget is spent."* They did
neither. Two said so directly:

> "I stopped with budget remaining because I could not find any action sequence
> that changes that arithmetic—not because the budget ran out."
> — `lf52/lf52-r3`

> "I never pinned down the vertical arm's exact push/drag rule, so I couldn't
> build a reliable plan, and I chose to stop rather than burn the remaining
> budget on guesses."
> — `sk48/sweep1`

Every game that produced a loss was run seven to eleven times, so the losing
session can be compared with other sessions that cleared the same level:

| game | level | quitter's moves on the level | winners' average | moves left |
|---|---:|---:|---:|---:|
| bp35 | 9 | **85** | 157 | 1,989 |
| bp35 | 8 | **52** | 92 | 2,162 |
| sk48 | 6 | **104** | 105 | 2,028 |
| sp80 | 5 | 195 | 57 | 2,218 |
| lf52 | 6 | 354 | 143 | 1,726 |
| lf52 | 7 | 396 | 164 | 1,391 |

The first three quit before spending as many moves as winning runs needed.
`bp35/sweep1` is the clearest example. Its earlier levels had cost 20, 50, 36,
25, 49, 43, and 64 moves. It spent 52 on level 8, declared that an undiscovered
mechanic was required, and stopped with 2,162 moves left.

The other three spent more than the winners. Much of that effort went into
building and searching increasingly complete models of the game.

## The uncertainty was already in the notebook

All six early exits named a gap in their own account. Five stopped without
testing it.

| run | what it still did not know | moves left | tested it? |
|---|---|---:|---|
| `sk48/sweep1` | "exact push/drag semantics for the vertical arm" | 2,028 | no |
| `bp35/sweep1` | "one mechanic in level 8 is still undiscovered" | 2,162 | no |
| `bp35/sealed` | a corridor "I never physically stood in" | 1,989 | no |
| `lf52/sweep2` | visible rail it could not pan far enough to inspect | 1,391 | no |
| `sp80/sealed2` | "specific untested leads for anyone continuing" | 2,218 | no |
| `lf52/lf52-r3` | "a mechanic I could not find" | 1,726 | partly; nine tested |

The five skipped experiments would each have taken between one and ten moves.
The agents stopped with 1,391–2,218 moves left.

This was not a failure to say the right thing about uncertainty. One conclusion
was headed **"IMPOSSIBILITY PROOF (within the verified model)"** and ended
"unless a mechanic outside this model exists." The qualification is accurate.
The behavior that followed it is the problem.

`lf52/lf52-r3` had even written itself this rule after level 4:

> "Don't conclude 'unsolvable/isolated' until the whole world has been swept."

Two levels later it concluded that the game was unsolvable and stopped with
1,726 moves left. The warning was still in `notes.md`, the file it re-read
whenever its conversation memory was trimmed.

There is a useful counterexample in `cn04/archive`. It proved that the goal as
it understood it could not be reached, then spent its remaining 2,380 moves on
the real game testing other possible goals. It ended with "that's an honest
gap, not a solved problem." The same model can respond correctly to this kind
of uncertainty. It does not do so reliably.

## Deep search in an incomplete model

The two `lf52` losses show why the early exits can look reasonable. Both built
good models and searched them carefully.

`lf52/lf52-r3` enumerated all 4,620 states allowed by its rules, checked that
the game's own "no moves left" signal agreed with its model at every dead end,
and tested nine alternative mechanics on the live game. One of the facts in
its notebook was:

> "[The red piece] cannot board a shuttle (verified: red could not jump over a
> loaded shuttle into an empty one)."

A winning run recorded a different transition:

> "A red can be jumped into an empty shuttle and carried."

Those are not the same experiment. The losing run tested one way of entering a
shuttle and promoted the result into a general rule. Its exhaustive proof was
valid under that rule.

A resumed analysis of `lf52/v2rest20` went further. It compared its move
predictions with 109 legal-move highlights from the stored game log without a
single mismatch, then searched 655,440 states. Its impossibility proof came
down to the camera:

> "cam <= 92 for the rest of the level. […] The entry jump […] needs cam >= 99.
> => level 6 is unwinnable unless a mechanic outside this model exists."

In other words, the required piece would be off-screen at the moment it needed
to be clicked. The move rules could be right while the display model was
wrong. Winning sessions disagreed about that display model: one said the camera
followed all green pieces; another avoided modeling it and moved a piece toward
the unseen region to make the camera reveal it.

The resumed agent knew some assumption had to be wrong, but searched the one
finite checklist available to it: the buttons. It had tried six of seven and
called `ACTION5` "the only untested lever left." Across eleven sessions of
`lf52` and 9,792 moves, nobody pressed `ACTION5`, including all seven winners.
The missing information was in a rule it believed it had already established.

Simulators make this failure sharper. They are one of the main reasons the
harness works: an agent can test thousands of plans without spending moves in
the real game. But a simulator only searches the rules already inside it.
`sp80/sealed2` tried about **70 million** block arrangements in simulation,
spent **195 moves** on the actual level, declared it impossible, and stopped
with 2,218 moves left.

The useful moments are when the real game attacks the simulator. One losing
run wrote that "the game then disproved the simulator's one unverified
assumption." Another reported two supposedly verified plans rejected by
reality, adding: "Each divergence taught me a rule." Some runs seek those
contradictions on purpose. `sk48/sweep1-again` built a real position just to
test its assumed win condition, fired both pins, and watched the level fail to
clear. Other runs treat a contradiction as an execution failure.

## Other failures

Not every loss follows the early-surrender pattern.

`wa30` gives one useful pair. A winning session organized its notebook around
objects with different roles: an orange **helper**, a purple **saboteur**, and
a textured **soft wall**. A losing session kept the same characters as "NPC A,"
"thief A," and "thief C" and never separated the helper from the saboteur. The
winner finished in 915 moves; the loser used 2,461 and failed two of nine
levels.

That is an illustration, not a population-level result. Across all 191
sessions, notebook organization does not predict winning: 47% of headings name
a level in both groups.

Another `wa30` run found the correct strategy but found it too late. It killed
both saboteurs and finished one step from placing the final box when the timer
expired. That was a scheduling failure, not a false impossibility proof. Four
of the fourteen non-wins used essentially their whole action budget, and four
others ended because of the server, my infrastructure, or conversation memory.

## What I take from it

The narrow claim is not that Opus is generally overconfident, or that every
loss has one cause. It is that six voluntary early exits share a specific
behavior: the model records uncertainty, searches deeply inside its current
world model, and then treats failure to find a plan as a reason to stop rather
than a reason to spend the remaining budget trying to break the model.

The prompt already warns against this, and one agent wrote the warning into its
own notebook. More instructions are unlikely to be the whole answer. The
winning runs instead turn uncertainty into actions: visit the unseen corridor,
construct the state that should be impossible, or deliberately make the
simulator disagree with the game.

The model often records what remains unresolved, but does not reliably direct
its remaining budget at that uncertainty. The missing step is choosing an
information-gathering action, running it, and revising the model from the
result. The transcript makes the gap unusually easy to observe: an unresolved
question in `notes.md`, no corresponding experiment in the action log, and a
large budget left when the model stops.

## Fine print

- The sample is 191 Claude Opus 5 sessions on the 25 public games: 177 wins and
  14 non-wins. Thirteen non-wins had a 2,500-move budget and one had 2,440. A
  handful of early winning sessions used smaller budgets.
- The 14 non-wins come from seven games, with half from `lf52` and `wa30`, so
  they are not independent observations. Each of those games was run 7–11
  times; that repetition enables the same-level comparisons above.
- Two non-wins belong to infrastructure rather than the model. The ARC server
  deleted `lf52/v2rest20` before its resumed session could act; the reasoning
  quoted here came from analysis of the previous session's stored log.
  `s5i5/sweep1` recovered from a similar deletion and was still working when my
  harness cut it off.
- Twelve of the 14 losing notebooks contain impossibility language, compared
  with 39 of 177 winning notebooks: 86% versus 22%. This is descriptive, not
  diagnostic; a stuck run naturally writes about being stuck. The behavioral
  signal is stopping with moves left.
- The losing runs tried slightly more distinct action types on the same games:
  5.14 of seven, compared with 4.84 for winners. That does not measure
  state-space exploration; it only rules out the narrow explanation that they
  failed because they touched fewer buttons. Notebook organization was the
  same between groups, and thinking per move did not separate them either.
