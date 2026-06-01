from deepturn_agents.models.findings import DiagnosticFinding


class SynthesisAgent:
    def rank(self, findings: list[DiagnosticFinding]) -> tuple[DiagnosticFinding, list[DiagnosticFinding]]:
        ordered = sorted(findings, key=lambda f: f.confidence, reverse=True)
        return ordered[0], ordered

    def aggregate_confidence(self, ordered: list[DiagnosticFinding]) -> float:
        if not ordered:
            return 0.2
        top = ordered[0].confidence
        runner_up = ordered[1].confidence if len(ordered) > 1 else top
        disagreement_penalty = 0.10 if abs(top - runner_up) > 0.35 else 0.0
        aggregate = (0.7 * top) + (0.3 * runner_up) - disagreement_penalty
        return max(0.2, min(0.95, aggregate))
