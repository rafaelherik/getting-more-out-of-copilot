from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPolicy:
    allowed_namespaces: set[str]
    max_log_bytes: int
    max_log_seconds: int

    def authorize_logs(self, namespace: str, bytes_requested: int, seconds_requested: int) -> tuple[bool, str]:
        if namespace not in self.allowed_namespaces:
            return False, "namespace_not_allowed"
        if bytes_requested > self.max_log_bytes:
            return False, "log_bytes_exceeded"
        if seconds_requested > self.max_log_seconds:
            return False, "log_window_exceeded"
        return True, "allowed"
