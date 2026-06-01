from deepturn_agents.models.findings import DiagnosticReport


def to_markdown(report: DiagnosticReport) -> str:
    lines = [
        f"# Investigation {report.investigation_id}",
        "## Summary",
        f"Overall confidence: {report.confidence:.2f}",
    ]
    if report.evidence_gaps:
        lines.append("## Evidence gaps")
        lines.extend([f"- {gap}" for gap in report.evidence_gaps])
    lines.append("## Findings")
    for finding in report.findings:
        lines.append(f"- {finding.hypothesis} ({finding.confidence:.2f})")
    lines.append("## Manual validation")
    for finding in report.findings:
        for step in finding.manual_validation_steps:
            lines.append(f"- {step}")
    return "\n".join(lines)
