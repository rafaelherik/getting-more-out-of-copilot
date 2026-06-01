from dataclasses import dataclass
from deepturn_agents.sanitization.redactor import redact_text


class ToolExecutionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class LogResult:
    text: str
    metadata: dict[str, str]


class ToolGateway:
    def __init__(self, adapter, policy, audit_log=None):
        self.adapter = adapter
        self.policy = policy
        self.audit_log = audit_log

    def get_logs(self, namespace: str, pod: str, container: str, seconds: int, limit_bytes: int) -> LogResult:
        allowed, reason = self.policy.authorize_logs(namespace, limit_bytes, seconds)
        if not allowed:
            return LogResult(text="", metadata={"policy_reason": reason})
        try:
            raw = self.adapter.get_logs(
                namespace=namespace,
                pod=pod,
                container=container,
                seconds=seconds,
                limit_bytes=limit_bytes,
            )
        except TimeoutError as exc:
            raise ToolExecutionError("log_timeout", str(exc)) from exc
        except PermissionError as exc:
            raise ToolExecutionError("log_permission_denied", str(exc)) from exc
        except Exception as exc:  # pragma: no cover
            raise ToolExecutionError("log_unknown_error", str(exc)) from exc
        redacted = redact_text(raw)
        if self.audit_log is not None:
            self.audit_log.write(
                {
                    "tool": "get_logs",
                    "namespace": namespace,
                    "policy_reason": reason,
                    "redactions": redacted.stats,
                }
            )
        return LogResult(text=redacted.sanitized_text, metadata={"policy_reason": reason})

    def get_pod_info(self, namespace: str, workload_ref: str) -> list[dict]:
        try:
            return self.adapter.get_pod_info(namespace=namespace, workload_ref=workload_ref)
        except TimeoutError as exc:
            raise ToolExecutionError("pod_info_timeout", str(exc)) from exc
        except PermissionError as exc:
            raise ToolExecutionError("pod_info_permission_denied", str(exc)) from exc
        except Exception as exc:  # pragma: no cover
            raise ToolExecutionError("pod_info_unknown_error", str(exc)) from exc

    def get_events(self, namespace: str, workload_ref: str, since_seconds: int) -> list[dict]:
        try:
            return self.adapter.get_events(
                namespace=namespace,
                workload_ref=workload_ref,
                since_seconds=since_seconds,
            )
        except TimeoutError as exc:
            raise ToolExecutionError("events_timeout", str(exc)) from exc
        except PermissionError as exc:
            raise ToolExecutionError("events_permission_denied", str(exc)) from exc
        except Exception as exc:  # pragma: no cover
            raise ToolExecutionError("events_unknown_error", str(exc)) from exc
