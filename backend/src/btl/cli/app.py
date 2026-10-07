"""The `btl` command and its subcommands."""

import typer

app = typer.Typer(
    name="btl",
    help="Generate synthetic football matches and inspect their events, values, and concept tags.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Between the Lines data engine."""
