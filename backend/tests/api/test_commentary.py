from btl.api.commentary import ACTION_WORDS, ZONE_WORDS, action_words, feed_words
from btl.learn.match_feed import FeedEntry, FeedKind, Flank, FoulGives, ShotEnd
from btl.learn.play_by_play import Zone
from btl.schema.ids import PlayerId, TeamId
from btl.schema.vocab import ActionType, Result


def test_every_action_and_zone_has_words() -> None:
    assert set(ACTION_WORDS) == set(ActionType)
    assert set(ZONE_WORDS) == set(Zone)


def test_a_shot_that_goes_in_says_so_and_any_other_action_is_just_what_was_done() -> None:
    assert action_words(ActionType.SHOT, Result.SUCCESS) == "shoots and scores"
    assert action_words(ActionType.SHOT, Result.FAIL) == "shoots"
    assert action_words(ActionType.CORNER_CROSSED, Result.FAIL) == "takes the corner"
    assert action_words(ActionType.PASS, Result.SUCCESS) == "passes"


def words(entry: FeedEntry) -> tuple[str, str]:
    names = {PlayerId(1): "de Witkamp", PlayerId(2): "Ferreiro"}
    clubs = {TeamId(1): "Ripon Wardens", TeamId(2): "Ludlow Ferrymen"}
    return feed_words(
        entry,
        names.__getitem__,
        clubs.__getitem__,
        lambda team: clubs[TeamId(3 - team)],
    )


def entry(
    kind: FeedKind,
    *players: int,
    period: int = 1,
    shot_end: ShotEnd | None = None,
    foul_gives: FoulGives | None = None,
    flank: Flank | None = None,
) -> FeedEntry:
    ids = tuple(PlayerId(p) for p in players)
    return FeedEntry(
        kind,
        period,
        0.0,
        0.0,
        TeamId(1),
        ids,
        shot_end=shot_end,
        foul_gives=foul_gives,
        flank=flank,
    )


def test_each_feed_entry_has_a_label_and_a_line() -> None:
    assert [
        words(entry(FeedKind.GOAL, 1)),
        words(entry(FeedKind.SHOT, 1, 2, shot_end=ShotEnd.SAVED)),
        words(entry(FeedKind.SHOT, 1)),
        words(entry(FeedKind.CORNER, 1, flank=Flank.RIGHT)),
        words(entry(FeedKind.THROW_IN, 1, 2, flank=Flank.LEFT)),
        words(entry(FeedKind.FOUL, 1, 2, foul_gives=FoulGives.FREE_KICK)),
        words(entry(FeedKind.FOUL, 1, 2)),
        words(entry(FeedKind.YELLOW_CARD, 1)),
        words(entry(FeedKind.MOVE, 1, 2)),
        words(entry(FeedKind.MOVE, 1)),
        words(entry(FeedKind.KICK_OFF, 1, 2, period=2)),
    ] == [
        ("Goal", "de Witkamp scores."),
        ("Shot · saved", "de Witkamp shoots; Ferreiro saves."),
        ("Shot", "de Witkamp shoots."),
        ("Corner", "Corner on the right, taken by de Witkamp."),
        ("Dead ball · throw-in", "Out off Ferreiro. Throw-in to Ripon Wardens, left touchline."),
        ("Foul", "de Witkamp fouls Ferreiro. Free kick to Ludlow Ferrymen."),
        ("Foul", "de Witkamp fouls Ferreiro."),
        ("Yellow card", "de Witkamp is booked."),
        ("Passing move · 2 players", ""),
        ("Passing move · 1 player", ""),
        ("Kick-off", "Second half under way."),
    ]


def test_every_kind_of_entry_has_words() -> None:
    for kind in FeedKind:
        label, _ = words(entry(kind, 1, 2))
        assert label
