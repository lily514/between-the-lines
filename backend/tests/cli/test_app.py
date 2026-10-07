from typer.testing import CliRunner

from btl.cli.app import app

runner = CliRunner()


def test_help_describes_the_tool() -> None:
    result = runner.invoke(app, ["--help"], env={"COLUMNS": "200"})

    assert result.exit_code == 0
    assert "synthetic football matches" in result.output
