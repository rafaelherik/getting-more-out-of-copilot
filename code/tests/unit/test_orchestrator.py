import pytest
from pydantic import ValidationError
from deepturn_agents.models.triggers import InvestigationTrigger
from deepturn_agents.models.findings import DiagnosticFinding
from deepturn_agents.orchestration.orchestrator import InvestigationOrchestrator
from deepturn_agents.tools.tool_gateway import ToolExecutionError


def test_trigger_and_finding_minimum_contract() -> None:
    trigger = InvestigationTrigger(
        cluster_id="cluster-a",
        namespace="default",
        workload_ref="deploy/api",
        pod_refs=["api-123"],
        symptom_type="runtime",
        severity="high",
        observed_at="2026-05-16T10:00:00Z",
    )
    finding = DiagnosticFinding(
        hypothesis="CrashLoop due to failed health check",
        confidence=0.81,
        supporting_evidence_refs=["log:1"],
        contradicting_evidence_refs=[],
        manual_validation_steps=["kubectl describe pod api-123 -n default"],
    )
    assert trigger.symptom_type == "runtime"
    assert finding.confidence > 0.5


def test_trigger_rejects_invalid_literals() -> None:
    with pytest.raises(ValidationError):
        InvestigationTrigger(
            cluster_id="cluster-a",
            namespace="default",
            workload_ref="deploy/api",
            pod_refs=["api-123"],
            symptom_type="invalid",
            severity="critical",
            observed_at="2026-05-16T10:00:00Z",
        )


class FailingGateway:
    def get_pod_info(self, namespace: str, workload_ref: str):
        raise ToolExecutionError("pod_info_timeout", "tool timeout")


def test_orchestrator_records_evidence_gap_on_tool_failure() -> None:
    orchestrator = InvestigationOrchestrator(tool_gateway=FailingGateway(), specialists=[], synthesis=None)
    trigger = InvestigationTrigger(
        cluster_id="cluster-a",
        namespace="default",
        workload_ref="deploy/api",
        pod_refs=["api-1"],
        symptom_type="runtime",
        severity="high",
        observed_at="2026-05-16T10:00:00Z",
    )
    report = orchestrator.run(trigger)
    assert report.evidence_gaps == ["pod_info_timeout"]


def test_orchestrator_generates_unique_investigation_ids() -> None:
    class HealthyGateway:
        def get_pod_info(self, namespace: str, workload_ref: str):
            return []

    orchestrator = InvestigationOrchestrator(tool_gateway=HealthyGateway(), specialists=[], synthesis=None)
    trigger = InvestigationTrigger(
        cluster_id="cluster-a",
        namespace="default",
        workload_ref="deploy/api",
        pod_refs=["api-1"],
        symptom_type="runtime",
        severity="high",
        observed_at="2026-05-16T10:00:00Z",
    )
    r1 = orchestrator.run(trigger)
    r2 = orchestrator.run(trigger)
    assert r1.investigation_id != r2.investigation_id
