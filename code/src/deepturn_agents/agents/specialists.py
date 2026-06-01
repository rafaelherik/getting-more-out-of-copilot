import re
from deepturn_agents.models.findings import DiagnosticFinding

FINDING_RE = re.compile(
    r"hypothesis=(?P<hyp>.*?);\s*confidence=(?P<conf>0(\.\d+)?|1(\.0+)?)",
    re.IGNORECASE | re.DOTALL,
)


class RuntimeSpecialist:
    def __init__(self, runtime, owns_runtime: bool = False) -> None:
        self.runtime = runtime
        self.owns_runtime = owns_runtime

    async def analyze_async(self, trigger, pod_info) -> list[DiagnosticFinding]:
        raw = await self.runtime.complete_async("Analyze runtime instability using sanitized evidence.")
        match = FINDING_RE.search(raw)
        if match is None:
            confidence = 0.3
            hypothesis = "Insufficiently structured model output"
        else:
            confidence = float(match.group("conf"))
            hypothesis = match.group("hyp").strip()
        return [
            DiagnosticFinding(
                hypothesis=hypothesis,
                confidence=confidence,
                supporting_evidence_refs=["runtime:1"],
                contradicting_evidence_refs=[],
                manual_validation_steps=["kubectl describe pod <pod> -n <ns>"],
            )
        ]

    async def aclose(self) -> None:
        if not self.owns_runtime:
            return
        close = getattr(self.runtime, "aclose", None)
        if callable(close):
            await close()
