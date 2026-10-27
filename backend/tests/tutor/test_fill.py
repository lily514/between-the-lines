from btl.tutor.slots import fill

TEXT = "Breaking {lines_broken} lines into the {receiver_zone} raised expected threat."


def test_a_count_of_one_makes_the_noun_after_it_singular() -> None:
    values = {"lines_broken": "one", "receiver_zone": "middle third"}

    assert fill(TEXT, values) == "Breaking one line into the middle third raised expected threat."


def test_a_count_above_one_keeps_the_plural() -> None:
    values = {"lines_broken": "two", "receiver_zone": "final third"}

    assert fill(TEXT, values) == "Breaking two lines into the final third raised expected threat."


def test_a_digit_one_counts_as_one_too() -> None:
    values = {"transition_shots": "1", "settled_shots": "4"}

    assert fill("{transition_shots} shots against {settled_shots} shots", values) == (
        "1 shot against 4 shots"
    )


def test_only_the_noun_right_after_the_slot_changes() -> None:
    values = {"pressers": "one"}

    assert fill("{pressers} players closed in; other players held.", values) == (
        "one player closed in; other players held."
    )
