from pathlib import Path
from typer.testing import CliRunner
from deepturn_agents.cli import app

runner = CliRunner()


def test_crashloop_scenario_produces_runtime_hypothesis(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["investigate", "default/deploy-api", "--out-dir", str(tmp_path)],
        env={"DEEPTURN_TEST_SCENARIO": "crashloop"},
    )
    assert result.exit_code == 0
    assert "CrashLoop" in result.stdout
