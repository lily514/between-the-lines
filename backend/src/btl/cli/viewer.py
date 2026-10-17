"""The learning loop in the terminal: questions on an ASCII pitch, feedback, progress bars."""

from collections.abc import Callable, Mapping

from rich.console import Console
from rich.rule import Rule
from rich.text import Text

from btl.cli.render import pitch_picture
from btl.learn.evidence import EvidencePack
from btl.learn.grader import Answer, ChoiceAnswer
from btl.learn.session import Asked, MatchStart, Told
from btl.schema.frames import to_left_to_right

BAR_WIDTH = 20


class TerminalViewer:
    """A `btl.learn.session.Viewer` that asks and answers in the terminal."""

    def __init__(self, console: Console, read: Callable[[str], str]) -> None:
        """Print to ``console`` and read answers with ``read`` (given the prompt)."""
        self._console = console
        self._read = read

    def begin(self, start: MatchStart) -> None:
        """Announce the match and where the viewer stands."""
        show_match_start(self._console, start)

    def ask(self, asked: Asked) -> Answer:
        """Show the question and read A, B or C."""
        show_question(self._console, asked)
        keys = [option.key for option in asked.view.options]
        while True:
            reply = self._read(f"Your answer ({', '.join(keys)})").strip().upper()
            if reply in keys:
                return ChoiceAnswer(reply)
            self._console.print(f"Please type one of {', '.join(keys)}.")

    def tell(self, told: Told) -> None:
        """Show the verdict, the explanation, why the bars moved, and the bars."""
        show_feedback(self._console, told)

    def end(self, mastery: dict[str, float], asked: int) -> None:
        """Sum up the match."""
        self._console.print(Rule("Full time"))
        self._console.print(f"{asked} questions this match.")
        self._console.print(progress_bars(mastery))


def show_match_start(console: Console, start: MatchStart) -> None:
    """The match about to be watched, and the bars before it."""
    console.print(Rule(Text(f"Match {start.match_number}: {start.home} v {start.away}")))
    console.print(progress_bars(start.mastery))


def show_question(console: Console, asked: Asked) -> None:
    """Why it's asking now, the pitch, the question and the options."""
    pack = asked.pack
    console.print()
    console.print(Text(why_now(pack), style="bold"))
    picture = pack.picture
    marks = [(*o.target_at, o.key) for o in asked.view.options if o.target_at is not None]
    console.print(
        pitch_picture(
            to_left_to_right(asked.match),
            picture.action_id,
            show_path=bool(picture.path),
            marks=marks,
        )
    )
    console.print(asked.text, highlight=False)
    for option in asked.view.options:
        console.print(f"  {option.key}  {option.label}", highlight=False)


def show_feedback(console: Console, told: Told) -> None:
    """The verdict, the explanation and takeaway, the update sentence, and the bars."""
    style = "bold green" if told.grade.correct else "bold yellow"
    explanation = told.explanation
    if told.misconception is not None:
        explanation += f" A common mix-up: “{told.misconception}”"
    console.print(Text.assemble((told.verdict, style), " ", explanation), highlight=False)
    console.print(Text(f"Takeaway: {told.takeaway}", style="italic"))
    console.print(Text(told.update, style="dim"))
    console.print(progress_bars(told.mastery))


def why_now(pack: EvidencePack) -> str:
    """When the question is asked and why, e.g. "Dead ball (goal kick), 36:10 · about 31:02"."""
    timing = pack.timing
    if timing.delivery == "live" and timing.delivered_phase == "dead ball":
        return f"{timing.occurred_at} · live, as play stops"
    if timing.delivery == "live":
        return f"{timing.occurred_at} · live, in settled play"
    where = timing.delivered_phase.value.capitalize()
    if timing.restart:
        where += f" ({timing.restart})"
    return f"{where}, {timing.delivered_at} · about play at {timing.occurred_at}"


def progress_bars(mastery: Mapping[str, float], mastered: float = 0.95) -> Text:
    """One bar per concept, with its mastery as a percentage."""
    width = max(len(name) for name in mastery)
    lines = Text()
    for name, value in mastery.items():
        filled = round(value * BAR_WIDTH)
        style = "green" if value >= mastered else "cyan"
        lines.append(f"  {name.ljust(width)}  ")
        lines.append("█" * filled, style=style)
        lines.append("░" * (BAR_WIDTH - filled), style="dim")
        lines.append(f"  {round(value * 100):3d}%\n")
    return lines
