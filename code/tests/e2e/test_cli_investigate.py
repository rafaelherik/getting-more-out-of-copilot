from pathlib import Path
from typer.testing import CliRunner
from deepturn_agents.cli import app
from deepturn_agents.models.findings import DiagnosticReport

runner = CliRunner()


def test_investigate_writes_markdown_and_json_reports(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["investigate", "default/deploy-api", "--out-dir", str(tmp_path)],
        env={"DEEPTURN_TEST_SCENARIO": "crashloop"},
    )
    assert result.exit_code == 0
    md_files = list(tmp_path.glob("*.md"))
    json_files = list(tmp_path.glob("*.json"))
    assert len(md_files) == 1
    assert len(json_files) == 1
    loaded = DiagnosticReport.model_validate_json(json_files[0].read_text(encoding="utf-8"))
    assert loaded.investigation_id
    assert "## Findings" in md_files[0].read_text(encoding="utf-8")
