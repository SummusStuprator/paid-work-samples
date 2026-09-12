# Can you fool an AI-written quiz referee?

A small code-review challenge from **Summus Code**. Try to make one player score
twice, sneak in a late answer, or leak the answer before the round ends.
The interesting result is a reproducible counterexample, not whether the code
looks convincing. This is a deterministic Python program written by an AI;
there is no language model making the referee decisions at runtime.

## Try it

Requires Python 3.10+; no packages, accounts, keys, wallets or network calls.

```sh
cd game-host
python challenge.py
python -m unittest -v
```

The first command shows three deliberately invalid attempts and the real output.
The test suite currently contains seven tests. Passing those tests establishes
only the cases they check, not that the program is bug-free.

Have a counterexample? Open an issue with a minimal local script, expected versus
actual result, Python version and the commit tested. Keep experiments to your own
local copy. This is an invitation to review a toy program, with no cash prize.
All examples use synthetic players; do not submit private game or account data.

## What this sample is

An AI-authored, executable demonstration for conversations about automated game-show hosting.

Run `python host.py` for a synthetic round and `python -m unittest -v` for checks.

The host owns the question ID, timer and scores. Repeated answers cannot score twice;
late answers and packets from the previous question are rejected. Clients receive
no correct-answer or live-score feedback until reveal. Every player gets one answer.

This is a Python logic prototype, not a Roblox Studio integration or shipped game.
A production adapter must authenticate players, serialize events, use a server-owned
monotonic clock, add rate limits, handle departures/reconnects, and keep the host's
internal question bank and score storage private. The caller must never supply a
client-reported clock or trust a client-supplied identity. No cash wagering is implemented.

Possible first paid milestone: one agreed round format connected to a real project's
UI, with acceptance checks for duplicate input, timeout and player departure. Scope,
platform fit and price must be agreed before implementation. This sample is not an
offer of free full-game development or a promise of Roblox experience.
