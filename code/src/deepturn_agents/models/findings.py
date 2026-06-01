from pydantic import BaseModel, Field


class DiagnosticFinding(BaseModel):
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence_refs: list[str]
    contradicting_evidence_refs: list[str]
    manual_validation_steps: list[str]


class DiagnosticReport(BaseModel):
    investigation_id: str
    findings: list[DiagnosticFinding]
    evidence_gaps: list[str]
    confidence: float
