import asyncio
from uuid import uuid4
from deepturn_agents.models.findings import DiagnosticReport
from deepturn_agents.tools.tool_gateway import ToolExecutionError


class InvestigationOrchestrator:
    def __init__(self, tool_gateway, specialists, synthesis) -> None:
        self.tool_gateway = tool_gateway
        self.specialists = specialists
        self.synthesis = synthesis

    def run(self, trigger):
        return asyncio.run(self.run_async(trigger))

    async def run_async(self, trigger):
        evidence_gaps: list[str] = []
        findings = []
        try:
            pod_info = self.tool_gateway.get_pod_info(trigger.namespace, trigger.workload_ref)
        except ToolExecutionError as exc:
            pod_info = []
            evidence_gaps.append(exc.code)
        except TimeoutError:
            pod_info = []
            evidence_gaps.append("pod_info_timeout")
        except PermissionError:
            pod_info = []
            evidence_gaps.append("pod_info_permission_denied")
        except Exception:
            pod_info = []
            evidence_gaps.append("pod_info_unknown_error")

        for specialist in self.specialists:
            findings.extend(await specialist.analyze_async(trigger=trigger, pod_info=pod_info))

        if self.synthesis is not None and findings:
            _primary, ordered = self.synthesis.rank(findings)
            confidence = self.synthesis.aggregate_confidence(ordered)
        else:
            confidence = max((f.confidence for f in findings), default=0.2)
        return DiagnosticReport(
            investigation_id=f"inv-{uuid4().hex[:12]}",
            findings=findings,
            evidence_gaps=evidence_gaps,
            confidence=confidence,
        )
