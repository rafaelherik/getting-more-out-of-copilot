from deepturn_agents.policy.tool_policy import ToolPolicy


def test_policy_denies_out_of_scope_namespace() -> None:
    policy = ToolPolicy(allowed_namespaces={"default"}, max_log_bytes=4096, max_log_seconds=600)
    allowed, reason = policy.authorize_logs(namespace="payments", bytes_requested=1024, seconds_requested=120)
    assert allowed is False
    assert reason == "namespace_not_allowed"
