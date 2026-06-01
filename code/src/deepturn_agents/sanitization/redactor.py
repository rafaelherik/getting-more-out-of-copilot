import re
from dataclasses import dataclass
from math import log2

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
KEY_VALUE_SECRET_RE = re.compile(r"(?i)(api_key|secret|password|token|auth_token|authorization)=([^\s;]+)")
BEARER_RE = re.compile(r"(?i)bearer\s+([A-Za-z0-9\-._~+/]+=*)")
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
CONNECTION_RE = re.compile(r"(?i)(mongodb\+srv://[^\s]+|postgresql://[^\s]+|amqps?://[^\s]+)")
TOKENISH_RE = re.compile(r"[A-Za-z0-9+/=_\-]{24,}")


@dataclass(frozen=True)
class RedactionResult:
    sanitized_text: str
    stats: dict[str, int]


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(value)
    return -sum((n / length) * log2(n / length) for n in counts.values())


def redact_text(text: str) -> RedactionResult:
    email_count = len(EMAIL_RE.findall(text))
    secret_count = len(KEY_VALUE_SECRET_RE.findall(text))
    bearer_count = len(BEARER_RE.findall(text))
    jwt_count = len(JWT_RE.findall(text))
    connection_count = len(CONNECTION_RE.findall(text))
    sanitized = text
    sanitized = BEARER_RE.sub("Bearer [REDACTED_BEARER]", sanitized)
    sanitized = JWT_RE.sub("[REDACTED_JWT]", sanitized)
    sanitized = EMAIL_RE.sub("[REDACTED_EMAIL]", sanitized)
    sanitized = KEY_VALUE_SECRET_RE.sub(r"\1=[REDACTED_SECRET]", sanitized)
    sanitized = CONNECTION_RE.sub("[REDACTED_CONNECTION_STRING]", sanitized)

    entropy_hits = 0
    for token in TOKENISH_RE.findall(sanitized):
        if _entropy(token) >= 4.5:
            sanitized = sanitized.replace(token, "[REDACTED_HIGH_ENTROPY]")
            entropy_hits += 1

    return RedactionResult(
        sanitized_text=sanitized,
        stats={
            "email": email_count,
            "secret": secret_count,
            "bearer": bearer_count,
            "jwt": jwt_count,
            "connection": connection_count,
            "entropy": entropy_hits,
        },
    )
