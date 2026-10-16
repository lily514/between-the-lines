# Milestone 2d: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## T1 — Questions per concept (2026-10-16)

**Plan said:** one table per concept in `questions.py`, saying its form, how to build its options, and its quality rule.
**We did:** three tables, each in the module that already owned that piece:
- `QUESTIONS` in `questions.py`: the form and the options;
- `WORTH_TEACHING` in `candidates.py`: the quality rule (only concepts that have one);
- `FACTS` in `evidence.py`: what is known before answering, and what answers.

`ASKABLE` is now the keys of `QUESTIONS`, and a test checks that `FACTS` covers the same concepts.
**Why:** `evidence.py` imports `questions.py`, and `questions.py` imports `candidates.py`. One table holding all three would have to import from all of them and would create a circular import. Keeping each rule beside the code it replaces also keeps the diff small.
**Affects:** T7 adds each new concept to all three tables (two, where it has no quality rule).

The "no behaviour change" check was run by hand rather than as a test, since it compares before and after. The demo viewer's terminal output for seeds 7, 11 and 23 is identical, and so is every evidence pack (as JSON, including `pack_id`) and every attempt for seeds 7, 11, 23, 41 and 99.
