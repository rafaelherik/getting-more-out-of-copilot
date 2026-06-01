import asyncio
from deepturn_agents.agents.specialists import RuntimeSpecialist
from deepturn_agents.agents.synthesis import SynthesisAgent
from deepturn_agents.models.findings import DiagnosticFinding, DiagnosticReport
from deepturn_agents.reporting.composer import to_markdown


class StubRuntime:
    async def complete_async(self, prompt: str) -> str:
        return "hypothesis=CrashLoop from probe failures;confidence=0.78"


def test_runtime_specialist_returns_structured_finding() -> None:
    specialist = RuntimeSpecialist(runtime=StubRuntime())
    findings = asyncio.run(specialist.analyze_async(trigger=None, pod_info=[]))
    assert len(findings) == 1
    assert findings[0].confidence == 0.78


def test_runtime_specialist_falls_back_on_malformed_output() -> None:
    class BadRuntime:
        async def complete_async(self, prompt: str) -> str:
            return "unexpected output"

    specialist = RuntimeSpecialist(runtime=BadRuntime())
    findings = asyncio.run(specialist.analyze_async(trigger=None, pod_info=[]))
    assert len(findings) == 1
    assert findings[0].confidence == 0.3


def test_runtime_specialist_disposes_owned_runtime_only() -> None:
    class ClosableRuntime:
        def __init__(self) -> None:
            self.closed = 0

        async def complete_async(self, prompt: str) -> str:
            return "hypothesis=ok;confidence=0.70"

        async def aclose(self) -> None:
            self.closed += 1

    owned = ClosableRuntime()
    external = ClosableRuntime()

    owned_specialist = RuntimeSpecialist(runtime=owned, owns_runtime=True)
    external_specialist = RuntimeSpecialist(runtime=external, owns_runtime=False)

    asyncio.run(owned_specialist.aclose())
    asyncio.run(external_specialist.aclose())

    assert owned.closed == 1
    assert external.closed == 0


def test_synthesis_picks_highest_confidence_primary() -> None:
    s = SynthesisAgent()
    findings = [
        DiagnosticFinding(
            hypothesis="A",
            confidence=0.41,
            supporting_evidence_refs=["a"],
            contradicting_evidence_refs=[],
            manual_validation_steps=["x"],
        ),
        DiagnosticFinding(
            hypothesis="B",
            confidence=0.83,
            supporting_evidence_refs=["b"],
            contradicting_evidence_refs=[],
            manual_validation_steps=["y"],
        ),
    ]
    primary, ordered = s.rank(findings)
    assert primary.hypothesis == "B"
    assert ordered[0].confidence == 0.83


def test_synthesis_aggregate_confidence_penalizes_disagreement() -> None:
    s = SynthesisAgent()
    findings = [
        DiagnosticFinding(
            hypothesis="A",
            confidence=0.92,
            supporting_evidence_refs=["a"],
            contradicting_evidence_refs=[],
            manual_validation_steps=["x"],
        ),
        DiagnosticFinding(
            hypothesis="B",
            confidence=0.30,
            supporting_evidence_refs=["b"],
            contradicting_evidence_refs=[],
            manual_validation_steps=["y"],
        ),
    ]
    _, ordered = s.rank(findings)
    aggregate = s.aggregate_confidence(ordered)
    assert aggregate < 0.92
    assert aggregate >= 0.2


def test_report_composer_includes_required_sections() -> None:
    report = DiagnosticReport(
        investigation_id="inv-123",
        findings=[
            DiagnosticFinding(
                hypothesis="CrashLoop due to probe timeout",
                confidence=0.83,
                supporting_evidence_refs=["log:1"],
                contradicting_evidence_refs=[],
                manual_validation_steps=["kubectl describe pod api-1 -n default"],
            )
        ],
        evidence_gaps=["events_timeout"],
        confidence=0.79,
    )
    md = to_markdown(report)
    assert "## Summary" in md
    assert "## Findings" in md
    assert "## Evidence gaps" in md
    assert "## Manual validation" in md
