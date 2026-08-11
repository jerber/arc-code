# How Opus 5 loses at ARC-AGI-3

The long version of [when the model is certain and
wrong](../README.md#when-the-model-is-certain-and-wrong). I ran Claude Opus 5
through this harness 191 times across the 25 public ARC-AGI-3 games. It won 177
of those sessions; 14 it did not. This is what happened in the 14, the patterns
they share, and what to make of them. It should not take any background to
follow. The numbers come from the run database; everything in quotes is the
model's own writing. Two of the sessions discussed here are published in full
under [`data/runs/`](../data/runs).

The short version: **the model almost never loses because the game out-lasted
it. It loses by convincing itself the level is impossible — with a careful
argument built on one belief it never thought to question — and then quitting
with most of its moves unused.** It describes its own uncertainty accurately.
Acting on that uncertainty is what's missing.

For reading what follows: each ARC-AGI-3 game is a small, unexplained video game
drawn on a 64×64 grid of colored pixels. The agent is told nothing about it — it
has to discover the controls, the goal, and the rules by trying things. A game
responds to at most seven inputs (ACTION1 through ACTION7 — think of them as
buttons, one of which is a click at a coordinate), and each session gets a
budget of 2,500 actions — individual presses, which
I'll call moves. The agent can write and run
any code it likes, and it keeps a notebook, `notes.md`, which is what survives
whenever its conversation memory fills up and gets trimmed. Sessions are named
game/run, like `lf52/sweep2`.

---

## 1. It quits with most of its moves unused

| how the run ended | runs | moves it still had |
|---|---|---|
| used the whole budget | 4 | 0–39 |
| **decided the level was impossible and quit** | **6** | **1,391–2,218** |
| my infrastructure cut it off while it was still working | 2 | 723–2,330 |
| the ARC server deleted the game mid-run | 1 | 1,712 |
| ran out of conversation memory | 1 | 1,734 |

The six that quit walked away from a median of about 2,000 of their 2,500
moves — 80% of the budget. The last line of [`PROMPT.md`](../PROMPT.md) is an
instruction: *"Play until `./act status` reports you have won or the budget is
spent."* Quitting early breaks it, and nothing in the model's sign-off suggests
it noticed. These are not exhausted runs. Two say the opposite outright:

> "I stopped with budget remaining because I could not find any action sequence
> that changes that arithmetic — not because the budget ran out." — `lf52/lf52-r3`

> "I never pinned down the vertical arm's exact push/drag rule, so I couldn't
> build a reliable plan, and I chose to stop rather than burn the remaining
> budget on guesses." — `sk48/sweep1`

The four that did spend the budget behaved well. One, `cn04/archive`, proved
that the goal as it understood it could not be reached, then spent its remaining
2,380 moves testing other possible goals on the real game, and closed with
"that's an honest gap, not a solved problem."

## 2. Three of the six quit before trying as hard as winning took

Every game that produced a loss was also run seven to eleven times in total, so
for each level that stopped a run, at least five other sessions cleared that
exact level. That makes effort directly comparable. Here are the six quitters —
what each spent on its final level, next to what winning runs spent clearing the
same level:

| game | level | moves the quitter spent there | winners' average on that level | moves the quitter still had |
|---|---|---|---|---|
| bp35 | 9 | **85** | 157 | 1,989 |
| bp35 | 8 | **52** | 92 | 2,162 |
| sk48 | 6 | **104** | 105 | 2,028 |
| sp80 | 5 | 195 | 57 | 2,218 |
| lf52 | 6 | 354 | 143 | 1,726 |
| lf52 | 7 | 396 | 164 | 1,391 |

The top three never reached the effort level that winning took. `bp35/sweep1` is
the sharpest case: its solved levels cost it 20, 50, 36, 25, 49, 43, and 64
moves. The level it declared to need "an undiscovered mechanic": 52. It gave the
level that beat it no more effort than the ones that didn't, then stopped with
2,162 moves in the bank.

The bottom three spent more than the winners. Where that extra effort went is
the next section.

## 3. The proof is careful. The belief under it isn't.

The three quitters that outspent the winners did not spend the surplus on the
game. They spent it proving their own theory self-consistent.

The proofs are genuinely good work. `lf52/lf52-r3` wrote a program that visited
every one of the 4,620 positions its rules allowed, confirmed that the game's
own "no moves left" indicator agreed with its rules at every dead end, and
tested nine alternative mechanics on the live game to rule them out.
`lf52/v2rest20`, another loss on the same level, checked its movement rules
against the game itself — when you
click a piece, the game highlights the legal moves, and the model compared its
predictions against 109 of those highlights without a single miss — then
searched 655,440 positions.

The problem is what the conclusion silently rests on. These game worlds can be
bigger than the screen; the "camera" is just which 64×64 window you currently
see. `v2rest20` had worked out an exact rule for when the camera moves, and its
impossibility proof turns out to be entirely about that rule:

> "cam <= 92 for the rest of the level. […] The entry jump […] needs cam >= 99.
> => level 6 is unwinnable unless a mechanic outside this model exists."

Translated: *the piece I need to click will always be off-screen when the moment
comes.* Every step is sound. But every step is about what the model believed it
would be shown — a fact about the display, promoted into a law of the game.

Sessions that won the same level treated the display with more suspicion, and
wrote the caution down as a rule:

> "**Never conclude '1 peg left' from the visible count alone.**" — `lf52/sealed`

> "Off-screen cells are treated as walls, so if a level needs a far region,
> first move a peg that way (the camera follows pegs) and re-run." — `lf52/sweep1`

That second one is describing a tool that does no camera math at all: treat
whatever you can't see as unknown, move a piece toward it, and look again. One
agent reasoned inside its model of the unknown; the winners went and looked. The
winners cleared level 6 in 143 moves on average. `lf52-r3` quit after 354, with
a proof, holding 1,726.

## 4. It says the right words about doubt. The words change nothing.

The losing runs are not overconfident in what they *say*. One headed its
conclusion **"IMPOSSIBILITY PROOF (within the verified model)"** and added
"unless a mechanic outside this model exists" — exactly the right disclaimers,
in exactly the right places. And `lf52/lf52-r3` had already written itself the
rule, in its own notebook, right after clearing level 4:

> "**Don't conclude 'unsolvable/isolated' until the whole world has been
> swept** — drive shuttles in all 4 directions to reveal it."

Two levels later it concluded unsolvable, with 1,726 moves unspent. The notebook
is the one file the model re-reads every time its memory is trimmed, so its own
warning was in front of it the whole time. The principle is not missing.
Following it is.

All six quitters left the same signature: a gap they named themselves, moves to
spare, and — in five of the six — no experiment.

| run | the gap it named | moves left | tried it? |
|---|---|---|---|
| `sk48/sweep1` | "Unresolved: exact push/drag semantics for the vertical arm" | 2,028 | no |
| `bp35/sweep1` | "one mechanic in level 8 is still undiscovered; the untested candidates are listed at the end of `notes.md`" | 2,162 | no |
| `bp35/sealed` | "hidden in a part of the chamber or the row −8/−9 corridor **I never physically stood in**" | 1,989 | no |
| `lf52/sweep2` | "There is visible rail past world x107 that I could not pan to […] I believe there's a dock or network link out there I never found" | 1,391 | no |
| `sp80/sealed2` | "level 5 uses a mechanic that none of the animations expose […] the specific untested leads for anyone continuing" | 2,218 | no |
| `lf52/lf52-r3` | "Either this level is unsolvable as generated, or there is a mechanic I could not find" | 1,726 | partly — it tested nine other mechanics, all inside its existing rules |

Each of the skipped experiments costs between one and ten moves.

So the model's language about uncertainty and its behavior under uncertainty
have come apart. I'd guess that's because the language is what gets checked —
and it shows: the hedges are accurate, the disclaimers correctly scoped, the
untested leads faithfully listed — while nothing checks whether the next hundred
moves respond to any of it. The gap is easy to catch automatically in a
transcript: an idea named in the notebook, absent from the game log, with moves
left over.

## 5. When it hunts for its own mistake, it checks the wrong list

`lf52/v2rest20` knew its theory had to be wrong somewhere — it said so. So where
did it look? At the one list that can be finished: the buttons. Seven possible
inputs, six pressed, and it named the seventh as "the only untested lever left
is ACTION5."

That was a dead end. Across eleven sessions of that game and 9,792 moves, **no
session ever pressed ACTION5 — including all seven winners.** The missing facts
were never behind an unpressed button. One was a property of a piece the model
had been pushing around for hundreds of moves — the red piece can leapfrog
without capturing, which is the key to the level. The other was the camera rule
its proof stood on, and that is exactly where its sibling sessions disagreed:
one run decided the camera rigidly follows a loaded shuttle; a winning run
decided it centers on all the green pegs; another winning run refused to model
the camera at all. Three incompatible beliefs about the same
game. The losing proof stands on one of them, and the model never pointed its
suspicion there — because the camera rule was the thing it had verified most
carefully.

A checklist gets searched because it can be completed. "Which of my beliefs is
this conclusion standing on, and how sure am I of it really?" has no bottom, so
it never gets asked. And to close off the obvious counter-theory: the losers did
not explore less. On these games the losing runs pressed more distinct buttons
than the winners did — 5.14 of 7 on average, against 4.84.

## 6. A different way to lose: it never names what it's seeing

`wa30` gives a clean side-by-side — same game, same model, same prompt. One
session wins in 915 moves; another loses in 2,461.

The winner's notebook is 71 lines organized around the things in the game, each
with a name, a job, and a rule of thumb:

> `O` solid Orange = **HELPER** npc (moves blocks onto my targets)
> `V` solid Purple = **SABOTEUR** npc […] Facing it and pressing ACTION5
> DESTROYS it (one action, gone for good).
> `#` dithered 1/2 texture = **soft wall**: player/NPCs cannot enter, BLOCKS CAN sit in it

(`O` and `V` are how orange and purple pixels print in the game log.) It even
derived a formula for reading each level's hidden time limit off a progress bar.

The loser's notebook is 129 lines organized by level number, and the same
characters stay anonymous the whole game: "NPC A," "thief A," "thief C." It
never split the orange creature that helps you from the purple creature that
robs you into two kinds with opposite jobs, and it never found the time-limit
formula. It failed 2 of 9 levels while spending 2.7× the moves.

One caution, because it cuts against a tidy story: across all 191 sessions, how
a notebook is organized does not predict winning — 47% of notebook headings name
a specific level in both groups, to the percentage point. This pair is a vivid
illustration, not a statistic.

And one loss doesn't fit the giving-up pattern at all. `wa30/maxeffort` found
the winning idea and simply ran out of time:

> "The answer, found late: a box in a **board corner** has only two grab cells,
> and the diagonal cell touches both — so a thief that commits to it must step
> beside me. On the final attempt both thieves were dead by bar 35, and I
> finished holding the 12th box one step from a free slot when the timer
> expired. The recipe works; I found it about two attempts too late."

That's a scheduling failure — the right discovery arrived two attempts too
late — not a surrender.

## 7. It trusts its imagination over the game

Most sessions build a simulator: a small program that plays a private copy of
the game under the rules as the model currently understands them, so that
candidate plans can be tested by the thousand without spending real moves.
[`PROMPT.md`](../PROMPT.md) suggests this once; the model does it everywhere,
and it's a big part of why the harness works.

What nothing regulates is the ratio of imagined experiments to real ones.
`sp80/sealed2` tested about **70 million** block arrangements inside its
simulator, spent **195 moves** on the actual level, declared it impossible, and
quit holding 2,218. Nothing in the loop says: *you have run seventy million
experiments in your imagination and 195 in reality, and every impossibility you
have found is a fact about the imagination.*

The runs themselves report the danger:

> "the game then disproved the simulator's one unverified assumption" — `bp35/sweep1`

> "I twice built a fully 'verified' plan (32 and 72 actions) that reality
> rejected partway […] Each divergence taught me a rule" — `s5i5/sweep1`

That last clause is the point. The moment the real game contradicts your
simulator is the most informative moment in the whole session — and the best
runs engineer that moment on purpose. `sk48/sweep1-again` refused to assume the
win condition and built a real position just to watch it fail ("fired both pins,
and the level did **not** clear"). `sk48/sealed` stranded a block by accident,
and instead of treating it as bad luck, turned it into a rule its planner
checked forever after: "**search with an 'all blocks reachable' invariant.**"

## 8. What to make of it

These are general failure modes, not quirks of these games — humans make them
too: trusting a careful argument over a cheap experiment, quitting with budget
to spare, doubting everything except the assumption doing the work.
Instructions don't seem to reach them: the prompt warns against the first two,
and the model broke a rule it had written for itself. But the model also
writes the needed rules on its own, and in the winning sessions it follows
them. So I'd generally expect failure modes like these to dissipate as models
get larger and more high-quality reinforcement learning goes into them.

## The fine print

- 191 sessions of Claude Opus 5 across the 25 public games; 177 wins, 14
  non-wins. Thirteen of the fourteen losses had the full 2,500-move budget; the
  fourteenth had 2,440. (A handful of early winning sessions ran with smaller
  budgets.) Numbers come from the run database; quotes come from the agents'
  notebooks and final reports, both preserved per session.
- The 14 losses come from just 7 games, half from `lf52` and `wa30` alone, so
  they are not 14 independent observations. Each of those games was run 7–11
  times in total — that repetition is what makes the same-level comparisons in
  §2 possible.
- Two of the 14 belong to the infrastructure, not the model. The ARC server
  deleted `lf52/v2rest20`'s game before the session could act; it is quoted here
  for its reasoning, which it did from the previous session's logs at zero move
  cost, not for its quitting. `s5i5/sweep1` recovered from the same kind of
  deletion, re-earned its levels, and was still searching when my harness cut it
  off.
- On language: 12 of the 14 losing notebooks contain impossibility language
  ("impossible," "unsolvable," "cannot be won," and variants) versus 39 of the
  177 winning ones — 86% against 22%. The count matches words, so it also
  catches warnings like "don't conclude unsolvable." That's descriptive, not
  diagnostic; a stuck run naturally writes about being stuck. The measure that
  matters is behavioral: moves left at the moment of quitting.
- Explanations I tested and rejected, recorded so nobody re-runs them: the
  losers explore *more* of the input space, not less (5.14 of 7 buttons versus
  the winners' 4.84 on the same games); notebook organization is identical
  between groups (47% of headings name a level in both); and the amount of
  thinking per move separates nothing (slightly higher in losses overall, but
  the per-game extremes run in both directions).
