"""The web API: the HTTP routes the web page calls to play the learning loop.

It is a thin layer over `btl.learn.session`, as the CLI is for the terminal. The server keeps no
session in memory: each request replays the viewer's current match from their saved answers up
to the next unanswered question, which works because a match replays exactly (see
`btl.learn.session`). The page itself lives in ``frontend/``.
"""
