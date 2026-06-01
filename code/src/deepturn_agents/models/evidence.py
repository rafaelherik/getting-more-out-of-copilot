from pydantic import BaseModel


class PodStateEvidence(BaseModel):
    pod_name: str
    phase: str
    restart_count: int


class EventTimelineEvidence(BaseModel):
    reason: str
    message: str


class LogExcerptEvidence(BaseModel):
    pod_name: str
    container_name: str
    text: str


class SanitizedEvidenceBundle(BaseModel):
    pod_state: list[PodStateEvidence]
    events: list[EventTimelineEvidence]
    logs: list[LogExcerptEvidence]
    redaction_stats: dict[str, int]
    truncation_markers: list[str]
    source_provenance: list[str]
