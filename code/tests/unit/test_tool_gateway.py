from deepturn_agents.adapters.k8s_adapter import K8sReadOnlyAdapter, KubernetesClientAdapter
from deepturn_agents.audit.audit_log import AuditLog
from deepturn_agents.tools.tool_gateway import ToolGateway
from deepturn_agents.policy.tool_policy import ToolPolicy


class FakeAdapter:
    def get_logs(self, namespace: str, pod: str, container: str, seconds: int, limit_bytes: int) -> str:
        return "token=abcd1234secret error: probe failed"


def test_gateway_applies_policy_and_redaction() -> None:
    audit = AuditLog(entries=[])
    gateway = ToolGateway(
        adapter=FakeAdapter(),
        policy=ToolPolicy(allowed_namespaces={"default"}, max_log_bytes=2048, max_log_seconds=300),
        audit_log=audit,
    )
    result = gateway.get_logs(namespace="default", pod="api-1", container="app", seconds=120, limit_bytes=512)
    assert "[REDACTED_SECRET]" in result.text
    assert result.metadata["policy_reason"] == "allowed"
    assert len(audit.entries) == 1
    assert audit.entries[0]["tool"] == "get_logs"
    assert "redactions" in audit.entries[0]


def test_kubernetes_adapter_implements_protocol() -> None:
    adapter = KubernetesClientAdapter()
    assert isinstance(adapter, K8sReadOnlyAdapter)
