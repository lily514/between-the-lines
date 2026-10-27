# Milestone 5 — Implementation notes

## T0 — Plan and design reference (2026-10-26)

**Plan said:** `design/` holds the handoff `.md` and the "Welcome redesign" export, unchanged.
**We did:** both are copied byte for byte, named `HANDOFF.md` (as every earlier milestone's handoff is) and
`Welcome-redesign.html`. The export bundles its boards as gzip-and-base64 pages inside a
`<script type="__bundler/manifest">`; nothing in the repo reads it, so it stays as delivered. Boards B2, B3 and B4
are one component with a different default flow (Before match 2, Before match 3, First look), so the three
share one scene catalogue and one step layout.
**Why:** full-word file names are the docs rule; the export is a reference, not data the app uses.
**Affects:** nothing.
