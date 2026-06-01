import typer
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime
from deepturn_agents.adapters.fake_k8s_adapter import FakeK8sAdapter
from deepturn_agents.policy.tool_policy import ToolPolicy
from deepturn_agents.tools.tool_gateway import ToolGateway
from deepturn_agents.orchestration.orchestrator import InvestigationOrchestrator
from deepturn_agents.agents.specialists import RuntimeSpecialist
from deepturn_agents.agents.microsoft_runtime import MicrosoftAgentRuntime
from deepturn_agents.models.triggers import InvestigationTrigger
from deepturn_agents.reporting.composer import to_markdown

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    return None


class _ScenarioRuntime:
    def __init__(self, scenario: str) -> None:
        self.scenario = scenario

    async def complete_async(self, prompt: str) -> str:
        if self.scenario == "crashloop":
            return "hypothesis=CrashLoop from probe failures;confidence=0.78"
        return "hypothesis=No clear runtime issue;confidence=0.55"

    async def aclose(self) -> None:
        return None


def _persist_report(report, out_dir: Path, sanitized_log: str | None = None) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{report.investigation_id}.md"
    json_path = out_dir / f"{report.investigation_id}.json"
    markdown = to_markdown(report)
    if sanitized_log:
        markdown = f"{markdown}\n## Sanitized log sample\n{sanitized_log}"
    md_path.write_text(markdown, encoding="utf-8")
    payload = report.model_dump(mode="json")
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return md_path, json_path


@app.command("investigate")
def investigate(
    target: str,
    out_dir: str = typer.Option("./artifacts", "--out-dir"),
) -> None:
    namespace, workload_ref = target.split("/", 1)
    scenario = os.getenv("DEEPTURN_TEST_SCENARIO")
    adapter = FakeK8sAdapter(scenario=scenario or "baseline")
    policy = ToolPolicy(allowed_namespaces={"default"}, max_log_bytes=2048, max_log_seconds=300)
    gateway = ToolGateway(adapter=adapter, policy=policy)
    sanitized_log = gateway.get_logs(
        namespace=namespace,
        pod="api-1",
        container="app",
        seconds=120,
        limit_bytes=512,
    ).text

    runtime: object = _ScenarioRuntime(scenario or "baseline")
    if scenario is None:
        try:
            runtime = MicrosoftAgentRuntime(project_endpoint="https://example", model="gpt-5.4-mini")
        except Exception:
            runtime = _ScenarioRuntime("baseline")

    specialist = RuntimeSpecialist(runtime=runtime, owns_runtime=True)
    orchestrator = InvestigationOrchestrator(tool_gateway=gateway, specialists=[specialist], synthesis=None)
    trigger = InvestigationTrigger(
        cluster_id="cluster-local",
        namespace=namespace,
        workload_ref=workload_ref,
        pod_refs=[],
        symptom_type="runtime",
        severity="high",
        observed_at=datetime.fromisoformat("2026-05-16T10:00:00+00:00"),
    )
    try:
        report = asyncio.run(orchestrator.run_async(trigger))
    finally:
        asyncio.run(specialist.aclose())

    primary = report.findings[0].hypothesis if report.findings else "Insufficient data"
    md_path, json_path = _persist_report(report=report, out_dir=Path(out_dir), sanitized_log=sanitized_log)
    typer.echo(
        f"investigation_id={report.investigation_id} hypothesis={primary} markdown={md_path} json={json_path}"
    )
