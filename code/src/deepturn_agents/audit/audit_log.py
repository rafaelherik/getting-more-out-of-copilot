from dataclasses import dataclass


@dataclass
class AuditLog:
    entries: list[dict]

    def write(self, event: dict) -> None:
        self.entries.append(event)
