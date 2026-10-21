from collections import Counter
from dataclasses import replace

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from btl.league.league import (
    MAX_STRENGTH,
    MIN_STRENGTH,
    N_CLUBS,
    SQUAD_NUMBERS,
    League,
    Role,
    generate_league,
    season_fixtures,
)
from btl.league.names import NAME_STYLES, NICKNAMES, pick_distinct, pick_style, possible_surnames


def league(seed: int) -> League:
    return generate_league(np.random.default_rng(seed))


def test_same_seed_gives_the_same_league() -> None:
    assert league(7) == league(7)


def test_different_seeds_give_different_leagues() -> None:
    assert league(7) != league(8)


@settings(max_examples=25, deadline=None)
@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_every_league_has_full_squads_with_unique_names_and_numbers(seed: int) -> None:
    generated = league(seed)

    assert len(generated.clubs) == N_CLUBS
    assert len({club.name for club in generated.clubs}) == N_CLUBS
    assert len({club.short_name for club in generated.clubs}) == N_CLUBS
    assert len({club.name.split()[-1] for club in generated.clubs}) == N_CLUBS
    players = [player for club in generated.clubs for player in club.squad]
    assert len({player.full_name for player in players}) == len(players)
    for club in generated.clubs:
        assert Counter(player.role for player in club.squad) == {
            role: len(numbers) for role, numbers in SQUAD_NUMBERS.items()
        }
        assert len({player.shirt_number for player in club.squad}) == len(club.squad)
        assert len({player.first_name for player in club.squad}) == len(club.squad)
        assert len({player.last_name for player in club.squad}) == len(club.squad)
        assert MIN_STRENGTH <= club.strength <= MAX_STRENGTH


def test_first_choice_goalkeeper_wears_number_one() -> None:
    for club in league(7).clubs:
        assert club.players(Role.GOALKEEPER)[0].shirt_number == 1


def test_ids_can_be_looked_up() -> None:
    generated = league(7)

    for club in generated.clubs:
        assert generated.club(club.team_id) is club
        for player in club.squad:
            assert player.team_id == club.team_id
            assert generated.player(player.player_id) is player


def test_season_has_every_club_host_every_other_club_once() -> None:
    fixtures = season_fixtures(league(7))

    assert len(fixtures) == N_CLUBS * (N_CLUBS - 1)
    assert len(set(fixtures)) == len(fixtures)
    assert all(home != away for home, away in fixtures)


def test_every_club_plays_once_per_round_and_hosts_half_its_games() -> None:
    fixtures = season_fixtures(league(7))
    per_round = N_CLUBS // 2

    for start in range(0, len(fixtures), per_round):
        round_clubs = [club for pair in fixtures[start : start + per_round] for club in pair]
        assert len(set(round_clubs)) == N_CLUBS
    assert set(Counter(home for home, _ in fixtures).values()) == {N_CLUBS - 1}


def test_season_needs_an_even_number_of_clubs() -> None:
    generated = league(7)

    with pytest.raises(ValueError, match="even"):
        season_fixtures(replace(generated, clubs=generated.clubs[:-1]))


def test_league_cannot_have_more_clubs_than_distinct_nicknames() -> None:
    with pytest.raises(ValueError, match="different items"):
        generate_league(np.random.default_rng(0), n_clubs=len(NICKNAMES) + 1)


def test_pick_distinct_never_repeats() -> None:
    picked = pick_distinct(np.random.default_rng(0), NICKNAMES, len(NICKNAMES))

    assert sorted(picked) == sorted(NICKNAMES)


def test_name_styles_appear_in_proportion_to_their_weights() -> None:
    rng = np.random.default_rng(0)
    draws = 20_000

    counts = Counter(pick_style(rng).name for _ in range(draws))

    total_weight = sum(style.weight for style in NAME_STYLES)
    for style in NAME_STYLES:
        assert counts[style.name] / draws == pytest.approx(style.weight / total_weight, abs=0.01)


def test_each_style_has_distinct_first_names_and_producible_surnames() -> None:
    for style in NAME_STYLES:
        assert len(set(style.first_names)) == len(style.first_names), style.name
        assert len(possible_surnames(style)) >= 20, style.name


def test_a_club_is_found_by_name_or_short_name_ignoring_case() -> None:
    league = generate_league(np.random.default_rng(0))
    club = league.clubs[3]

    assert league.find_club(club.short_name.lower()) == club
    assert league.find_club(f" {club.name.upper()} ") == club
    with pytest.raises(KeyError):
        league.find_club("nowhere")
