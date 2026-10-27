# Milestone 6 implementation notes

## T1 — The track (2026-10-27)
**Plan said:** the track covers the actions strictly before `names_until`, its last frame is the question picture,
and the verification checks that no track has a frame at or after its `names_until`.
**We did:** the actions strictly between where the viewer left off and the moment, then one closing keyframe at the
moment itself: the start of the action the question is about (its snapshot, and the ball at its start, without its
flight). That closing frame is the question picture. When the viewer left off at or past the moment, as after a
question saved for a stoppage, or when two questions share one action, the track is empty.
**Why:** a frame at the moment's start is the only way the last frame can be the picture; it shows where everyone
stood as the play began, nothing of how it turned out. The test checks that nothing comes after the moment.
**Affects:** T2's leak checks look for nothing *after* `names_until`; T3 and T4 handle an empty track by showing no
pitch.
