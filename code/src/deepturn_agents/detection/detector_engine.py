from datetime import datetime, timezone
from deepturn_agents.models.triggers import InvestigationTrigger


class DetectorEngine:
    def __init__(self, dedup_window_seconds: int) -> None:
        self.dedup_window_seconds = dedup_window_seconds
        self._seen: dict[str, datetime] = {}

    def _evict_old_seen(self, current: datetime) -> None:
        cutoff = current.timestamp() - (self.dedup_window_seconds * 2)
        self._seen = {k: v for k, v in self._seen.items() if v.timestamp() >= cutoff}

    def _parse_observed_at(self, raw: str) -> datetime | None:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    def from_watch_event(self, event: dict) -> InvestigationTrigger | None:
        key = f"{event['namespace']}|{event['workload_ref']}|{event['symptom_type']}"
        observed = self._parse_observed_at(event["observed_at"])
        if observed is None:
            return None
        self._evict_old_seen(observed)
        last = self._seen.get(key)
        if last is not None and (observed - last).total_seconds() < self.dedup_window_seconds:
            return None
        self._seen[key] = observed
        return InvestigationTrigger(
            cluster_id="cluster-local",
            namespace=event["namespace"],
            workload_ref=event["workload_ref"],
            pod_refs=event.get("pod_refs", []),
            symptom_type=event["symptom_type"],
            severity=event["severity"],
            observed_at=observed,
        )

    def from_reconciliation(self, snapshots: list[dict]) -> list[InvestigationTrigger]:
        triggers: list[InvestigationTrigger] = []
        now = datetime.now(timezone.utc)
        for item in snapshots:
            if item.get("anomaly") is True:
                triggers.append(
                    InvestigationTrigger(
                        cluster_id="cluster-local",
                        namespace=item["namespace"],
                        workload_ref=item["workload_ref"],
                        pod_refs=item.get("pod_refs", []),
                        symptom_type=item["symptom_type"],
                        severity=item["severity"],
                        observed_at=now,
                    )
                )
        return triggers
