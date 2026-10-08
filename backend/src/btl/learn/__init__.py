"""The learning engine: what the viewer knows, which moments to ask about, and how to ask.

Everything here is pure. It never reads the clock or the network, and it never changes a match:
the match is the same for every viewer, and adaptation lives in which moments are asked about,
when, and how.
"""
