from btl.tutor.slots import slotify

VALUES = {
    "player": "#10 Chinedu Trankwo",
    "occurred_at": "00:32",
    "delivered_at": "00:32",
    "score": "0\u20130",
    "team": "Ludlow Ferrymen",
    "lines_broken": "one",
    "A.label": "Corner to Ludlow Ferrymen",
    "answer": "Corner to Ludlow Ferrymen",
}


def test_values_written_out_become_their_slots() -> None:
    text = "Back at 00:32, #10 Chinedu Trankwo played it for Ludlow Ferrymen, at 0\u20130."

    assert slotify(text, VALUES) == (
        "Back at {occurred_at}, {player} played it for {team}, at {score}."
    )


def test_the_longest_value_wins_and_the_answer_beats_an_option_letter() -> None:
    assert slotify("It was a Corner to Ludlow Ferrymen.", VALUES) == "It was a {answer}."


def test_plain_words_and_existing_slots_are_left_alone() -> None:
    text = "It broke one line, as {player} wanted: {team} pressed on."

    assert slotify(text, VALUES) == text


def test_a_value_inside_a_longer_word_or_number_is_not_a_match() -> None:
    assert (
        slotify("At 100:325 the score read 10\u20130.", VALUES)
        == "At 100:325 the score read 10\u20130."
    )


def test_a_preferred_slot_wins_a_tie() -> None:
    values = {"team": "Hexham Anchors", "restart_team": "Hexham Anchors"}

    assert slotify("Hexham Anchors restart.", values) == "{team} restart."
    assert slotify("Hexham Anchors restart.", values, {"restart_team"}) == "{restart_team} restart."
