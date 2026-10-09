"""The Tutor: words around the evidence, pitched at the viewer's level.

A Tutor receives only the evidence pack (or, before an answer, the question view) and the
level inside it. It writes ``{slots}`` that name facts and never writes a number itself; code
fills the slots. It never imports the simulator, the threat model, the detectors or the planter.
"""
