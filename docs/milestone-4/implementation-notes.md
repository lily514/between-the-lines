# Milestone 4 — Implementation notes

## T1 — Matches and calendar (2026-10-23)

**Plan said:** each match gives its state, plus the score and question count when finished.
**We did:** a match in progress also gives a score, and the match clock it stands at. Both are taken at the last moment
the viewer answered about, never later.
**Why:** the Matches board's "Live now" card shows a score and clock, and the stepped match has no live clock to read
them from. The last moment answered is a point the viewer has already seen, so nothing ahead of them leaks.
**Affects:** T6 shows it on the in-progress card as "at {clock}".
