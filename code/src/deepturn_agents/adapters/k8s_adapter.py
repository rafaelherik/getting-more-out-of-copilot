from typing import Protocol, runtime_checkable


@runtime_checkable
class K8sReadOnlyAdapter(Protocol):
    def get_pod_info(self, namespace: str, workload_ref: str) -> list[dict]: ...
    def get_events(self, namespace: str, workload_ref: str, since_seconds: int) -> list[dict]: ...
    def get_logs(self, namespace: str, pod: str, container: str, seconds: int, limit_bytes: int) -> str: ...


class KubernetesClientAdapter:
    def get_pod_info(self, namespace: str, workload_ref: str) -> list[dict]:
        return []

    def get_events(self, namespace: str, workload_ref: str, since_seconds: int) -> list[dict]:
        return []

    def get_logs(self, namespace: str, pod: str, container: str, seconds: int, limit_bytes: int) -> str:
        return ""
