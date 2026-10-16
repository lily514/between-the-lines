"""SPADL vocabularies as enums.

Values are the SPADL ids, so ``ActionType.PASS == 0`` matches socceraction's ``type_id``.
socceraction keeps these as plain lists in ``socceraction.spadl.config``; a test checks that
the enums stay in step with them. ``Phase`` and ``ConceptId`` are our own additions.
"""

from enum import IntEnum, StrEnum


class ActionType(IntEnum):
    """What the player did with the ball."""

    PASS = 0
    CROSS = 1
    THROW_IN = 2
    FREEKICK_CROSSED = 3
    FREEKICK_SHORT = 4
    CORNER_CROSSED = 5
    CORNER_SHORT = 6
    TAKE_ON = 7
    FOUL = 8
    TACKLE = 9
    INTERCEPTION = 10
    SHOT = 11
    SHOT_PENALTY = 12
    SHOT_FREEKICK = 13
    KEEPER_SAVE = 14
    KEEPER_CLAIM = 15
    KEEPER_PUNCH = 16
    KEEPER_PICK_UP = 17
    CLEARANCE = 18
    BAD_TOUCH = 19
    NON_ACTION = 20
    DRIBBLE = 21
    GOALKICK = 22

    @property
    def spadl_name(self) -> str:
        """The name socceraction uses for this action type."""
        return self.name.lower()


class Result(IntEnum):
    """How the action turned out."""

    FAIL = 0
    SUCCESS = 1
    OFFSIDE = 2
    OWNGOAL = 3
    YELLOW_CARD = 4
    RED_CARD = 5

    @property
    def spadl_name(self) -> str:
        """The name socceraction uses for this result."""
        return self.name.lower()


class BodyPart(IntEnum):
    """Which part of the body the player used."""

    FOOT = 0
    HEAD = 1
    OTHER = 2
    HEAD_OTHER = 3
    FOOT_LEFT = 4
    FOOT_RIGHT = 5

    @property
    def spadl_name(self) -> str:
        """The name socceraction uses for this body part."""
        # SPADL's only name that isn't a valid identifier.
        return "head/other" if self is BodyPart.HEAD_OTHER else self.name.lower()


class Phase(StrEnum):
    """The kind of play an action belongs to. Not part of SPADL."""

    OPEN_PLAY = "open_play"
    SET_PIECE = "set_piece"
    TRANSITION = "transition"


class ConceptId(StrEnum):
    """The football concepts the detectors know. Each has exactly one detector."""

    SWITCH_OF_PLAY = "switch_of_play"
    LINE_BREAKING_PASS = "line_breaking_pass"
    COUNTER_PRESS = "counter_press"
    COUNTER_ATTACK = "counter_attack"
    RESTART = "restart"

    @property
    def label(self) -> str:
        """The concept's name for display, e.g. "switch of play"."""
        return self.value.replace("_", " ")
