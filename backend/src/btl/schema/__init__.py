"""Event schema for synthetic matches, compatible with socceraction's SPADL format.

Coordinate convention (the only one used in this package):

- The pitch is 105 x 68 metres. ``x`` runs along the length from 0 to 105, ``y`` across the
  width from 0 to 68, with the origin in the bottom-left corner.
- Stored events follow socceraction's converter output: the home team attacks left to right
  (towards x = 105) and the away team right to left, in both periods. Teams do not switch
  ends at half-time.
- Anything that needs the acting team to attack left to right, such as Expected Threat or
  the concept detectors, gets a normalised copy from ``frames.py``. No other module flips
  coordinates.
"""
