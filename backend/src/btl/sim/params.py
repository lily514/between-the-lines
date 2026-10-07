"""Every tunable number in the simulator, in one place.

Probabilities and lengths that depend on where the ball is are given per third of the pitch,
from the point of view of the team in possession. The values are calibrated so that matches
fall inside the bands in ``tests/sim/test_calibration.py``; they make no further claim to realism.
"""

from dataclasses import dataclass

from btl.sim.pitch import Third


@dataclass(frozen=True, slots=True)
class PerThird:
    """One value for each third of the pitch."""

    defensive: float
    middle: float
    attacking: float

    def of(self, third: Third) -> float:
        """The value for one third."""
        return {
            Third.DEFENSIVE: self.defensive,
            Third.MIDDLE: self.middle,
            Third.ATTACKING: self.attacking,
        }[third]


@dataclass(frozen=True, slots=True)
class SimParams:
    """The simulator's knobs. Lengths in metres, times in seconds, speeds in metres per second."""

    period_seconds: float = 45 * 60

    # Choosing an action. Shots and crosses are considered first; otherwise it's a pass or,
    # with ``dribble_share``, a dribble.
    shot_share_in_box: float = 0.22
    header_share_after_cross: float = 0.6
    shot_share_in_range: float = 0.035
    shot_range: float = 30.0
    cross_share_on_wing: float = 0.35
    dribble_share: PerThird = PerThird(0.15, 0.25, 0.3)

    # Passes: length from a gamma distribution, direction from a von Mises distribution centred
    # on the opponent's goal (higher kappa = more direct). Success depends on the third the pass
    # ends in, falling off for long passes.
    pass_length_mean: PerThird = PerThird(22.0, 18.0, 13.0)
    pass_length_shape: float = 2.0
    pass_kappa: PerThird = PerThird(1.0, 0.6, 0.2)
    pass_success: PerThird = PerThird(0.93, 0.85, 0.7)
    long_pass_from: float = 20.0
    long_pass_falloff: float = 30.0
    keeper_pass_length_mean: float = 35.0
    keeper_pass_kappa: float = 2.0

    dribble_length_mean: float = 8.0
    dribble_kappa: float = 1.5
    dribble_success: float = 0.88

    cross_success: float = 0.3
    keeper_claim_share: float = 0.35
    # Of the crosses that fail, the share a defender deflects out for a corner.
    cross_out_for_corner: float = 0.15

    # A failed pass carries on past its target by a random distance in this range. If that takes
    # it off the pitch, it goes out of play instead of to an opponent.
    run_on: tuple[float, float] = (0.0, 20.0)

    throw_in_length_mean: float = 12.0
    # The longest throws in real matches are in the low 30s of metres.
    throw_in_longest: float = 32.0
    # Throw-ins aim this many radians infield of straight up the touchline.
    throw_in_aim: float = 0.6
    throw_in_kappa: float = 2.0
    corner_short_share: float = 0.2
    corner_success: float = 0.3

    # Shots: chance of scoring is a logistic function of the goal's visible angle (radians) and
    # the distance to goal. Of the shots that don't score, ``save_share`` are saved.
    goal_intercept: float = -2.2
    goal_per_radian: float = 1.5
    goal_per_metre: float = -0.1
    save_share: float = 0.45
    # Of the shots that miss, the share deflected out for a corner rather than a goal kick.
    miss_out_for_corner: float = 0.1

    # A team's success odds are multiplied by (its strength / opponent's strength) ** this.
    strength_exponent: float = 0.5

    pass_speed: float = 15.0
    dribble_speed: float = 5.0
    control_time: tuple[float, float] = (0.8, 3.0)
    reaction_time: tuple[float, float] = (0.5, 1.5)
    shot_flight: float = 1.0
    # Dead-ball time before each kind of restart.
    goal_restart_delay: float = 45.0
    goal_kick_delay: float = 20.0
    throw_in_delay: float = 12.0
    corner_delay: float = 25.0

    # Actions this soon after winning the ball in open play count as a transition.
    transition_seconds: float = 8.0


DEFAULT_PARAMS = SimParams()
