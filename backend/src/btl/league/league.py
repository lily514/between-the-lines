"""A fictional league: its clubs, their squads, and a season of fixtures."""

from dataclasses import dataclass
from enum import StrEnum

from numpy.random import Generator

from btl.league.names import NICKNAMES, TOWNS, generate_player_name, pick_distinct
from btl.schema.ids import PlayerId, TeamId

LEAGUE_NAME = "Meridian League"
N_CLUBS = 10


class Role(StrEnum):
    """A player's position group in the squad."""

    GOALKEEPER = "GK"
    DEFENDER = "DF"
    MIDFIELDER = "MF"
    FORWARD = "FW"


# A 20-player squad, with the shirt numbers each group traditionally wears.
SQUAD_NUMBERS: dict[Role, tuple[int, ...]] = {
    Role.GOALKEEPER: (1, 13),
    Role.DEFENDER: (2, 3, 4, 5, 6, 15, 22),
    Role.MIDFIELDER: (8, 10, 14, 16, 17, 18),
    Role.FORWARD: (7, 9, 11, 19, 20),
}

# Club strength scales the simulator's success rates: 1.0 is an average side.
MIN_STRENGTH = 0.85
MAX_STRENGTH = 1.15


@dataclass(frozen=True, slots=True)
class Player:
    """A squad member. Player ids are ``team_id * 100 + squad index``, e.g. 304."""

    player_id: PlayerId
    team_id: TeamId
    first_name: str
    last_name: str
    role: Role
    shirt_number: int

    @property
    def full_name(self) -> str:
        """First name and surname, e.g. "Teo Hartwell"."""
        return f"{self.first_name} {self.last_name}"


@dataclass(frozen=True, slots=True)
class Club:
    """A club and its squad."""

    team_id: TeamId
    name: str
    short_name: str
    strength: float
    squad: tuple[Player, ...]

    def players(self, role: Role) -> tuple[Player, ...]:
        """The squad members in one position group."""
        return tuple(player for player in self.squad if player.role is role)


@dataclass(frozen=True, slots=True)
class League:
    """The whole league. Team ids run 1 … number of clubs."""

    name: str
    clubs: tuple[Club, ...]

    def club(self, team_id: TeamId) -> Club:
        """The club with this team id."""
        return self.clubs[team_id - 1]

    def player(self, player_id: PlayerId) -> Player:
        """The player with this player id."""
        club = self.club(TeamId(player_id // 100))
        return club.squad[player_id % 100 - 1]

    def find_club(self, name: str) -> Club:
        """The club with this name or short name, ignoring case ("HEX", "hexham anchors").

        Raises:
            KeyError: If no club has that name.
        """
        wanted = name.strip().casefold()
        for club in self.clubs:
            if wanted in (club.name.casefold(), club.short_name.casefold()):
                return club
        raise KeyError(name)


def _short_name(town: str, taken: set[str]) -> str:
    """A three-letter code like "KEN", trying later letters if the obvious code is taken."""
    letters = town.upper()
    for second in range(1, len(letters)):
        for third in range(second + 1, len(letters)):
            code = letters[0] + letters[second] + letters[third]
            if code not in taken:
                return code
    raise RuntimeError(f"no unused short name for {town}")


def _generate_squad(rng: Generator, team_id: TeamId, taken_names: set[str]) -> tuple[Player, ...]:
    squad: list[Player] = []
    first_names: set[str] = set()
    surnames: set[str] = set()
    for role, numbers in SQUAD_NUMBERS.items():
        for shirt_number in numbers:
            first, last = generate_player_name(rng, taken_names, first_names, surnames)
            taken_names.add(f"{first} {last}")
            first_names.add(first)
            surnames.add(last)
            squad.append(
                Player(
                    player_id=PlayerId(team_id * 100 + len(squad) + 1),
                    team_id=team_id,
                    first_name=first,
                    last_name=last,
                    role=role,
                    shirt_number=shirt_number,
                )
            )
    return tuple(squad)


def generate_league(rng: Generator, n_clubs: int = N_CLUBS) -> League:
    """Generate a league of fictional clubs with full squads.

    Args:
        rng: The league's own random stream. The same stream state always gives the same league.
        n_clubs: How many clubs to create.

    Returns:
        A league in which every club has its own town and nickname, e.g. "Kendal Kestrels",
        and every player's full name is unique.
    """
    towns = pick_distinct(rng, TOWNS, n_clubs)
    nicknames = pick_distinct(rng, NICKNAMES, n_clubs)
    short_names: set[str] = set()
    player_names: set[str] = set()
    clubs: list[Club] = []
    for index, (town, nickname) in enumerate(zip(towns, nicknames, strict=True)):
        team_id = TeamId(index + 1)
        short_name = _short_name(town, short_names)
        short_names.add(short_name)
        clubs.append(
            Club(
                team_id=team_id,
                name=f"{town} {nickname}",
                short_name=short_name,
                strength=round(float(rng.uniform(MIN_STRENGTH, MAX_STRENGTH)), 3),
                squad=_generate_squad(rng, team_id, player_names),
            )
        )
    return League(name=LEAGUE_NAME, clubs=tuple(clubs))


def season_fixtures(league: League) -> tuple[tuple[TeamId, TeamId], ...]:
    """A double round robin: every club hosts every other club once.

    Uses the circle method, so each round every club plays exactly once. The second half of
    the season repeats the first with home and away swapped.

    Returns:
        ``(home_team_id, away_team_id)`` pairs, round by round.
    """
    team_ids = [club.team_id for club in league.clubs]
    if len(team_ids) % 2:
        raise ValueError("season_fixtures needs an even number of clubs")
    rounds: list[list[tuple[TeamId, TeamId]]] = []
    rotation = team_ids[1:]
    for round_index in range(len(team_ids) - 1):
        circle = [team_ids[0], *rotation]
        half = len(circle) // 2
        pairs = list(zip(circle[:half], reversed(circle[half:]), strict=True))
        # Alternate who hosts the fixed club so it isn't at home every week.
        rounds.append([(b, a) if round_index % 2 else (a, b) for a, b in pairs])
        rotation = rotation[-1:] + rotation[:-1]
    second_half = [[(away, home) for home, away in round_pairs] for round_pairs in rounds]
    return tuple(pair for round_pairs in rounds + second_half for pair in round_pairs)
