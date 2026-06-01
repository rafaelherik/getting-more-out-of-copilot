from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class InvestigationTrigger(BaseModel):
    cluster_id: str
    namespace: str
    workload_ref: str
    pod_refs: list[str]
    symptom_type: Literal["runtime", "scheduling", "network", "resource", "startup"]
    severity: Literal["low", "medium", "high"]
    observed_at: datetime
