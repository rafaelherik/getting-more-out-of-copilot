class FakeK8sAdapter:
    def __init__(self, scenario: str) -> None:
        self.scenario = scenario

    def get_pod_info(self, namespace: str, workload_ref: str) -> list[dict]:
        if self.scenario == "crashloop":
            return [{"pod_name": "api-1", "phase": "Running", "restart_count": 19}]
        return [{"pod_name": "api-1", "phase": "Running", "restart_count": 0}]

    def get_events(self, namespace: str, workload_ref: str, since_seconds: int) -> list[dict]:
        if self.scenario == "crashloop":
            return [{"reason": "BackOff", "message": "Back-off restarting failed container"}]
        return []

    def get_logs(self, namespace: str, pod: str, container: str, seconds: int, limit_bytes: int) -> str:
        if self.scenario == "crashloop":
            return "error: liveness probe failed token=abcd1234secret"
        return "token=abcd1234secret ok"
