"""The planter: spreads the requested moments over a match and writes each one when it is due."""

from dataclasses import dataclass

from numpy.random import Generator

from btl.league.league import Club
from btl.plant.spec import PlantRequest
from btl.plant.templates import TEMPLATES
from btl.schema.match import Match
from btl.sim.chain import Side, Start
from btl.sim.engine import simulate_match
from btl.sim.params import DEFAULT_PARAMS, SimParams
from btl.sim.script import Script
from btl.sim.shape import FOUR_FOUR_TWO, Formation

# No moment in a period's first or last few minutes, so none is cut off by the whistle and
# each has play around it.
QUIET_START = 5 * 60.0
QUIET_END = 5 * 60.0


@dataclass(frozen=True, slots=True)
class Planter:
    """A `btl.sim.script.Director` that plants the requested moments, easiest first.

    The moments' target times are spread evenly over both halves, leaving out each half's first
    and last ``QUIET_START`` and ``QUIET_END`` seconds. Each is planted at the first possession
    on or after its target that its template can use.
    """

    request: PlantRequest
    params: SimParams = DEFAULT_PARAMS

    def __post_init__(self) -> None:
        """Check every concept can be planted."""
        for moment in self.request.moments:
            if moment.concept not in TEMPLATES:
                raise ValueError(f"{moment.concept} can't be planted yet")

    @property
    def targets(self) -> tuple[tuple[int, float], ...]:
        """When each moment is due, in match order: its period, and seconds into it."""
        half = self.params.period_seconds - QUIET_START - QUIET_END
        count = len(self.request.moments)
        targets: list[tuple[int, float]] = []
        for index in range(count):
            into_play = (index + 0.5) / count * 2 * half
            period, into_half = divmod(into_play, half)
            targets.append((int(period) + 1, QUIET_START + into_half))
        return tuple(targets)

    def script(
        self,
        planted: int,
        period_id: int,
        clock: float,
        attack: Side,
        defence: Side,
        start: Start,
        rng: Generator,
    ) -> Script | None:
        """The next moment's opening, if it is due and this possession can hold it."""
        moments = self.request.in_match_order
        if planted >= len(moments) or (period_id, clock) < self.targets[planted]:
            return None
        if clock > self.params.period_seconds - QUIET_END:
            return None
        moment = moments[planted]
        template = TEMPLATES[moment.concept]
        if not template.fits(start):
            return None
        return template.write(attack, defence, start, moment.difficulty, rng, self.params)


def simulate_with_moments(
    home: Club,
    away: Club,
    seed: int,
    request: PlantRequest,
    *,
    home_formation: Formation = FOUR_FOUR_TWO,
    away_formation: Formation = FOUR_FOUR_TWO,
    with_snapshots: bool = True,
    params: SimParams = DEFAULT_PARAMS,
) -> Match:
    """Simulate a match holding the requested moments, easiest first.

    Play before the first moment is the same as in the match without any. The arguments are
    as for `btl.sim.engine.simulate_match`.

    Raises:
        RuntimeError: If the match ended before every moment could be planted.
    """
    match = simulate_match(
        home,
        away,
        seed,
        home_formation=home_formation,
        away_formation=away_formation,
        with_snapshots=with_snapshots,
        params=params,
        director=Planter(request, params),
    )
    if len(match.planted) < len(request.moments):
        raise RuntimeError(
            f"only {len(match.planted)} of {len(request.moments)} moments could be planted"
        )
    return match
