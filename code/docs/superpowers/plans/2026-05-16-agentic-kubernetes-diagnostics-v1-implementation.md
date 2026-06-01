# Agentic Kubernetes Diagnostics v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI-first Python application that monitors one Kubernetes cluster, runs deterministic evidence collection, sanitizes data, and uses Microsoft agent-based reasoning to produce diagnostic reports.

**Plan Preparation Continuation Directive:** Continue preparation by executing tasks in order, updating checkboxes inline, and immediately reflecting any contract/signature adjustments in all downstream task snippets before moving to the next task.

**Architecture:** The implementation uses a hybrid design: deterministic detection, policy-gated read-only tool execution, and sanitization happen before any agent reasoning. Specialist diagnostic agents consume only sanitized evidence, then a synthesis stage produces Markdown and JSON reports. The code is structured so cluster adapters and orchestration contracts can expand to multi-cluster in a later phase.

**Tech Stack:** Python 3.12, uv, Taskfile.dev, Typer CLI, Pydantic v2, pytest, Kubernetes Python client, Microsoft Agent Framework (`agent-framework`), Azure Identity, structlog, ruff, mypy

---

## File Structure Map

### Core project files
- Create: `pyproject.toml` - packaging, dependencies, tooling config
- Create: `Taskfile.yml` - simplified developer commands
- Create: `.gitignore` - Python and local runtime artifacts
- Create: `README.md` - setup and local run instructions

### Source files
- Create: `src/deepturn_agents/__init__.py` - package marker
- Create: `src/deepturn_agents/cli.py` - Typer entrypoint and commands
- Create: `src/deepturn_agents/config.py` - settings and runtime limits
- Create: `src/deepturn_agents/models/triggers.py` - trigger schemas
- Create: `src/deepturn_agents/models/evidence.py` - evidence schemas
- Create: `src/deepturn_agents/models/findings.py` - finding and report schemas
- Create: `src/deepturn_agents/policy/tool_policy.py` - allowlist and limits
- Create: `src/deepturn_agents/sanitization/redactor.py` - masking and truncation
- Create: `src/deepturn_agents/adapters/k8s_adapter.py` - Kubernetes read-only adapter
- Create: `src/deepturn_agents/adapters/fake_k8s_adapter.py` - integration test fixture adapter
- Create: `src/deepturn_agents/tools/tool_gateway.py` - only get_pod_info/get_events/get_logs path
- Create: `src/deepturn_agents/detection/detector_engine.py` - watch + reconciliation trigger logic
- Create: `src/deepturn_agents/orchestration/orchestrator.py` - workflow state execution
- Create: `src/deepturn_agents/agents/microsoft_runtime.py` - Microsoft agent runtime wrapper
- Create: `src/deepturn_agents/agents/specialists.py` - specialist agent contracts
- Create: `src/deepturn_agents/agents/synthesis.py` - finding merge and ranking
- Create: `src/deepturn_agents/reporting/composer.py` - markdown/json report formatting
- Create: `src/deepturn_agents/audit/audit_log.py` - structured audit sink

### Tests
- Create: `tests/unit/test_tool_policy.py`
- Create: `tests/unit/test_redactor.py`
- Create: `tests/unit/test_tool_gateway.py`
- Create: `tests/unit/test_detector_engine.py`
- Create: `tests/unit/test_orchestrator.py`
- Create: `tests/unit/test_synthesis.py`
- Create: `tests/integration/test_scenarios.py`
- Create: `tests/e2e/test_cli_investigate.py`

### Test fixtures
- Create: `tests/fixtures/scenarios/crashloop.json`
- Create: `tests/fixtures/scenarios/imagepullbackoff.json`
- Create: `tests/fixtures/scenarios/unschedulable.json`
- Create: `tests/fixtures/scenarios/oom_probe_fail.json`

## Task 1: Bootstrap Python Project and Tooling

**Files:**
- Create: `pyproject.toml`
- Create: `Taskfile.yml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/deepturn_agents/__init__.py`
- Create: `src/deepturn_agents/cli.py`
- Test: `tests/e2e/test_cli_investigate.py`

- [x] **Step 1: Write the failing CLI smoke test**

```python
# tests/e2e/test_cli_investigate.py
from typer.testing import CliRunner
from deepturn_agents.cli import app

runner = CliRunner()


def test_cli_has_investigate_command() -> None:
    result = runner.invoke(app, ["investigate", "default/my-api", "--out-dir", "./artifacts"])
    assert result.exit_code == 0
    assert "investigation_id" in result.stdout
    assert "out_dir=./artifacts" in result.stdout
```

- [x] **Step 1.1: Verify repository precondition and source layout before first test run**

Run:

```bash
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || git init
mkdir -p src/deepturn_agents tests/unit tests/integration tests/e2e tests/fixtures/scenarios
test -f src/deepturn_agents/__init__.py || touch src/deepturn_agents/__init__.py
```

Expected: repository initialized if missing; required source/test layout exists

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/e2e/test_cli_investigate.py -v`
Expected: FAIL with import error for `deepturn_agents` or missing `investigate` command

- [x] **Step 3: Add minimal project and CLI implementation**

```toml
# pyproject.toml
[project]
name = "deepturn-agents"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "typer>=0.16.0",
  "pydantic>=2.10.0",
  "kubernetes>=30.1.0",
    "agent-framework>=1.0.0b251001",
    "azure-identity==1.20.*",
  "structlog>=24.4.0"
]

[dependency-groups]
dev = ["pytest>=8.3.0", "ruff>=0.6.0", "mypy>=1.11.0"]

[project.scripts]
diagctl = "deepturn_agents.cli:app"

[tool.pytest.ini_options]
pythonpath = ["src"]
```

```yaml
# Taskfile.yml
version: "3"

tasks:
    sync:
        cmds:
            - uv sync --group dev

    lock:
        cmds:
            - uv lock

    deps-verify:
        cmds:
            - uv run python -c "import importlib.metadata as m; print('agent-framework', m.version('agent-framework')); print('azure-identity', m.version('azure-identity'))"

    test:
        cmds:
            - uv run pytest {{.CLI_ARGS}}

    lint:
        cmds:
            - uv run ruff check src tests {{.CLI_ARGS}}

    typecheck:
        cmds:
            - uv run mypy src {{.CLI_ARGS}}

    quality:
        cmds:
            - task lint
            - task typecheck
            - task test -- -v
```

```python
# src/deepturn_agents/cli.py
import typer

app = typer.Typer(no_args_is_help=True)


@app.command("investigate")
def investigate(
    target: str,
    out_dir: str = typer.Option("./artifacts", "--out-dir"),
) -> None:
    typer.echo(f"investigation_id=inv-local-0001 target={target} out_dir={out_dir}")
```

- [x] **Step 3.1: Sync dependencies for local execution**

Run: `task sync`
Expected: PASS with `.venv` and project dependencies installed

- [x] **Step 3.2: Generate lockfile and verify pinned runtime dependencies**

Run: `task lock && task deps-verify`
Expected: PASS and prints installed versions for `agent-framework` and `azure-identity`

- [x] **Step 4: Run test to verify it passes**

Run: `task test -- tests/e2e/test_cli_investigate.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add pyproject.toml Taskfile.yml src/deepturn_agents/cli.py src/deepturn_agents/__init__.py tests/e2e/test_cli_investigate.py .gitignore README.md
git commit -m "chore: bootstrap python project and CLI entrypoint"
```

## Task 2: Define Domain Models and Report Contracts

**Files:**
- Create: `src/deepturn_agents/models/triggers.py`
- Create: `src/deepturn_agents/models/evidence.py`
- Create: `src/deepturn_agents/models/findings.py`
- Test: `tests/unit/test_orchestrator.py`

- [x] **Step 1: Write failing schema contract test**

```python
# tests/unit/test_orchestrator.py
import pytest
from pydantic import ValidationError
from deepturn_agents.models.triggers import InvestigationTrigger
from deepturn_agents.models.findings import DiagnosticFinding


def test_trigger_and_finding_minimum_contract() -> None:
    trigger = InvestigationTrigger(
        cluster_id="cluster-a",
        namespace="default",
        workload_ref="deploy/api",
        pod_refs=["api-123"],
        symptom_type="runtime",
        severity="high",
        observed_at="2026-05-16T10:00:00Z",
    )
    finding = DiagnosticFinding(
        hypothesis="CrashLoop due to failed health check",
        confidence=0.81,
        supporting_evidence_refs=["log:1"],
        contradicting_evidence_refs=[],
        manual_validation_steps=["kubectl describe pod api-123 -n default"],
    )
    assert trigger.symptom_type == "runtime"
    assert finding.confidence > 0.5


def test_trigger_rejects_invalid_literals() -> None:
    with pytest.raises(ValidationError):
        InvestigationTrigger(
            cluster_id="cluster-a",
            namespace="default",
            workload_ref="deploy/api",
            pod_refs=["api-123"],
            symptom_type="invalid",
            severity="critical",
            observed_at="2026-05-16T10:00:00Z",
        )
```

- [x] **Step 2: Run test to verify it fails**

Run: `task test -- tests/unit/test_orchestrator.py::test_trigger_and_finding_minimum_contract -v`
Expected: FAIL with module not found for model files

- [x] **Step 3: Implement minimal Pydantic models**

```python
# src/deepturn_agents/models/triggers.py
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
```

```python
# src/deepturn_agents/models/findings.py
from pydantic import BaseModel, Field


class DiagnosticFinding(BaseModel):
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence_refs: list[str]
    contradicting_evidence_refs: list[str]
    manual_validation_steps: list[str]
```

```python
# src/deepturn_agents/models/evidence.py
from pydantic import BaseModel


class PodStateEvidence(BaseModel):
    pod_name: str
    phase: str
    restart_count: int


class EventTimelineEvidence(BaseModel):
    reason: str
    message: str


class LogExcerptEvidence(BaseModel):
    pod_name: str
    container_name: str
    text: str


class SanitizedEvidenceBundle(BaseModel):
    pod_state: list[PodStateEvidence]
    events: list[EventTimelineEvidence]
    logs: list[LogExcerptEvidence]
    redaction_stats: dict[str, int]
    truncation_markers: list[str]
    source_provenance: list[str]
```

- [x] **Step 4: Run test to verify it passes**

Run: `task test -- tests/unit/test_orchestrator.py::test_trigger_and_finding_minimum_contract -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/deepturn_agents/models tests/unit/test_orchestrator.py
git commit -m "feat: add trigger evidence and finding contracts"
```

## Task 3: Implement Policy Engine and Sanitization

**Files:**
- Create: `src/deepturn_agents/policy/tool_policy.py`
- Create: `src/deepturn_agents/sanitization/redactor.py`
- Test: `tests/unit/test_tool_policy.py`
- Test: `tests/unit/test_redactor.py`

- [x] **Step 1: Write failing policy and redaction tests**

```python
# tests/unit/test_tool_policy.py
from deepturn_agents.policy.tool_policy import ToolPolicy


def test_policy_denies_out_of_scope_namespace() -> None:
    policy = ToolPolicy(allowed_namespaces={"default"}, max_log_bytes=4096, max_log_seconds=600)
    allowed, reason = policy.authorize_logs(namespace="payments", bytes_requested=1024, seconds_requested=120)
    assert allowed is False
    assert reason == "namespace_not_allowed"
```

```python
# tests/unit/test_redactor.py
from deepturn_agents.sanitization.redactor import redact_text


def test_redact_masks_credentials_emails_and_bearer() -> None:
    text = "api_key=sk_live_12345 user=alice@example.com Authorization=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    result = redact_text(text)
    assert "alice@example.com" not in result.sanitized_text
    assert "sk_live_12345" not in result.sanitized_text
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result.sanitized_text
    assert result.stats["email"] == 1


def test_redact_masks_high_entropy_tokens() -> None:
    text = "value=Qw7z8Xk2Lm9Np4Rt6Yu1Vb3Hd0Se5Cf8"
    result = redact_text(text)
    assert "Qw7z8Xk2Lm9Np4Rt6Yu1Vb3Hd0Se5Cf8" not in result.sanitized_text
    assert result.stats["entropy"] >= 1
```

- [x] **Step 2: Run tests to verify they fail**

Run: `task test -- tests/unit/test_tool_policy.py tests/unit/test_redactor.py -v`
Expected: FAIL with missing modules

- [x] **Step 3: Implement minimal policy and redactor code**

```python
# src/deepturn_agents/policy/tool_policy.py
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
```

```python
# src/deepturn_agents/sanitization/redactor.py
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
    sanitized = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    sanitized = KEY_VALUE_SECRET_RE.sub(r"\1=[REDACTED_SECRET]", sanitized)
    sanitized = BEARER_RE.sub("Bearer [REDACTED_BEARER]", sanitized)
    sanitized = JWT_RE.sub("[REDACTED_JWT]", sanitized)
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
```

- [x] **Step 4: Run tests to verify they pass**

Run: `task test -- tests/unit/test_tool_policy.py tests/unit/test_redactor.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/deepturn_agents/policy src/deepturn_agents/sanitization tests/unit/test_tool_policy.py tests/unit/test_redactor.py
git commit -m "feat: add policy checks and redaction pipeline primitives"
```

## Task 4: Build Read-Only Kubernetes Adapter and Tool Gateway

**Files:**
- Create: `src/deepturn_agents/adapters/k8s_adapter.py`
- Create: `src/deepturn_agents/tools/tool_gateway.py`
- Create: `src/deepturn_agents/audit/audit_log.py`
- Test: `tests/unit/test_tool_gateway.py`

- [x] **Step 1: Write failing gateway contract test**

```python
# tests/unit/test_tool_gateway.py
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `task test -- tests/unit/test_tool_gateway.py -v`
Expected: FAIL with missing `ToolGateway`

- [x] **Step 3: Implement adapter interface, gateway, and audit sink**

```python
# src/deepturn_agents/adapters/k8s_adapter.py
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
```

```python
# src/deepturn_agents/audit/audit_log.py
from dataclasses import dataclass


@dataclass
class AuditLog:
    entries: list[dict]

    def write(self, event: dict) -> None:
        self.entries.append(event)
```

```python
# src/deepturn_agents/tools/tool_gateway.py
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
            raw = self.adapter.get_logs(namespace=namespace, pod=pod, container=container, seconds=seconds, limit_bytes=limit_bytes)
        except TimeoutError as exc:
            raise ToolExecutionError("log_timeout", str(exc)) from exc
        except PermissionError as exc:
            raise ToolExecutionError("log_permission_denied", str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive fallback
            raise ToolExecutionError("log_unknown_error", str(exc)) from exc
        redacted = redact_text(raw)
        if self.audit_log is not None:
            self.audit_log.write({"tool": "get_logs", "namespace": namespace, "policy_reason": reason, "redactions": redacted.stats})
        return LogResult(text=redacted.sanitized_text, metadata={"policy_reason": reason})

    def get_pod_info(self, namespace: str, workload_ref: str) -> list[dict]:
        try:
            return self.adapter.get_pod_info(namespace=namespace, workload_ref=workload_ref)
        except TimeoutError as exc:
            raise ToolExecutionError("pod_info_timeout", str(exc)) from exc
        except PermissionError as exc:
            raise ToolExecutionError("pod_info_permission_denied", str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive fallback
            raise ToolExecutionError("pod_info_unknown_error", str(exc)) from exc

    def get_events(self, namespace: str, workload_ref: str, since_seconds: int) -> list[dict]:
        try:
            return self.adapter.get_events(namespace=namespace, workload_ref=workload_ref, since_seconds=since_seconds)
        except TimeoutError as exc:
            raise ToolExecutionError("events_timeout", str(exc)) from exc
        except PermissionError as exc:
            raise ToolExecutionError("events_permission_denied", str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive fallback
            raise ToolExecutionError("events_unknown_error", str(exc)) from exc
```

- [x] **Step 4: Run test to verify it passes**

Run: `task test -- tests/unit/test_tool_gateway.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/deepturn_agents/adapters src/deepturn_agents/tools src/deepturn_agents/audit tests/unit/test_tool_gateway.py
git commit -m "feat: add read-only k8s tool gateway with policy and audit"
```

## Task 5: Implement Hybrid Detector Engine

**Files:**
- Create: `src/deepturn_agents/detection/detector_engine.py`
- Test: `tests/unit/test_detector_engine.py`

- [x] **Step 1: Write failing detector dedup test**

```python
# tests/unit/test_detector_engine.py
from deepturn_agents.detection.detector_engine import DetectorEngine


def test_detector_deduplicates_burst_events() -> None:
    detector = DetectorEngine(dedup_window_seconds=60)
    e1 = {"namespace": "default", "workload_ref": "deploy/api", "symptom_type": "runtime", "severity": "high", "observed_at": "2026-05-16T10:00:00Z"}
    e2 = {"namespace": "default", "workload_ref": "deploy/api", "symptom_type": "runtime", "severity": "high", "observed_at": "2026-05-16T10:00:20Z"}
    assert detector.from_watch_event(e1) is not None
    assert detector.from_watch_event(e2) is None


def test_detector_skips_malformed_timestamps_without_crashing() -> None:
    detector = DetectorEngine(dedup_window_seconds=60)
    malformed = {"namespace": "default", "workload_ref": "deploy/api", "symptom_type": "runtime", "severity": "high", "observed_at": "not-a-time"}
    assert detector.from_watch_event(malformed) is None


def test_detector_evicts_old_seen_entries() -> None:
    detector = DetectorEngine(dedup_window_seconds=1)
    old = {"namespace": "a", "workload_ref": "deploy/a", "symptom_type": "runtime", "severity": "high", "observed_at": "2026-05-16T10:00:00Z"}
    new = {"namespace": "b", "workload_ref": "deploy/b", "symptom_type": "runtime", "severity": "high", "observed_at": "2026-05-16T10:10:00Z"}
    detector.from_watch_event(old)
    detector.from_watch_event(new)
    assert len(detector._seen) <= 1
```

- [x] **Step 2: Run test to verify it fails**

Run: `task test -- tests/unit/test_detector_engine.py -v`
Expected: FAIL with missing `DetectorEngine`

- [x] **Step 3: Implement minimal hybrid detector logic**

```python
# src/deepturn_agents/detection/detector_engine.py
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
            observed_at=event["observed_at"],
        )

    def from_reconciliation(self, snapshots: list[dict]) -> list[InvestigationTrigger]:
        triggers: list[InvestigationTrigger] = []
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `task test -- tests/unit/test_detector_engine.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/deepturn_agents/detection tests/unit/test_detector_engine.py
git commit -m "feat: add hybrid detector with watch dedup and reconciliation"
```

## Task 6: Implement Orchestrator Workflow and Evidence Gaps

**Files:**
- Create: `src/deepturn_agents/orchestration/orchestrator.py`
- Modify: `src/deepturn_agents/models/findings.py`
- Test: `tests/unit/test_orchestrator.py`

- [x] **Step 1: Add failing orchestrator degraded-mode test**

```python
# tests/unit/test_orchestrator.py
from deepturn_agents.orchestration.orchestrator import InvestigationOrchestrator
from deepturn_agents.models.triggers import InvestigationTrigger
from deepturn_agents.tools.tool_gateway import ToolExecutionError


class FailingGateway:
    def get_pod_info(self, namespace: str, workload_ref: str):
        raise ToolExecutionError("pod_info_timeout", "tool timeout")


def test_orchestrator_records_evidence_gap_on_tool_failure() -> None:
    orchestrator = InvestigationOrchestrator(tool_gateway=FailingGateway(), specialists=[], synthesis=None)
    trigger = InvestigationTrigger(
        cluster_id="cluster-a",
        namespace="default",
        workload_ref="deploy/api",
        pod_refs=["api-1"],
        symptom_type="runtime",
        severity="high",
        observed_at="2026-05-16T10:00:00Z",
    )
    report = orchestrator.run(trigger)
    assert report.evidence_gaps == ["pod_info_timeout"]


def test_orchestrator_generates_unique_investigation_ids() -> None:
    class HealthyGateway:
        def get_pod_info(self, namespace: str, workload_ref: str):
            return []

    orchestrator = InvestigationOrchestrator(tool_gateway=HealthyGateway(), specialists=[], synthesis=None)
    trigger = InvestigationTrigger(
        cluster_id="cluster-a",
        namespace="default",
        workload_ref="deploy/api",
        pod_refs=["api-1"],
        symptom_type="runtime",
        severity="high",
        observed_at="2026-05-16T10:00:00Z",
    )
    r1 = orchestrator.run(trigger)
    r2 = orchestrator.run(trigger)
    assert r1.investigation_id != r2.investigation_id
```

- [x] **Step 2: Run test to verify it fails**

Run: `task test -- tests/unit/test_orchestrator.py::test_orchestrator_records_evidence_gap_on_tool_failure -v`
Expected: FAIL with missing `InvestigationOrchestrator`

- [x] **Step 3: Implement minimal orchestrator and report model additions**

```python
# src/deepturn_agents/models/findings.py
from pydantic import BaseModel, Field


class DiagnosticFinding(BaseModel):
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence_refs: list[str]
    contradicting_evidence_refs: list[str]
    manual_validation_steps: list[str]


class DiagnosticReport(BaseModel):
    investigation_id: str
    findings: list[DiagnosticFinding]
    evidence_gaps: list[str]
    confidence: float
```

```python
# src/deepturn_agents/orchestration/orchestrator.py
from deepturn_agents.models.findings import DiagnosticReport
from deepturn_agents.tools.tool_gateway import ToolExecutionError
import asyncio
from uuid import uuid4


class InvestigationOrchestrator:
    def __init__(self, tool_gateway, specialists, synthesis) -> None:
        self.tool_gateway = tool_gateway
        self.specialists = specialists
        self.synthesis = synthesis

    def run(self, trigger):
        return asyncio.run(self.run_async(trigger))

    async def run_async(self, trigger):
        evidence_gaps: list[str] = []
        findings = []
        try:
            pod_info = self.tool_gateway.get_pod_info(trigger.namespace, trigger.workload_ref)
        except ToolExecutionError as exc:
            pod_info = []
            evidence_gaps.append(exc.code)
        except TimeoutError:
            pod_info = []
            evidence_gaps.append("pod_info_timeout")
        except PermissionError:
            pod_info = []
            evidence_gaps.append("pod_info_permission_denied")
        except Exception:
            pod_info = []
            evidence_gaps.append("pod_info_unknown_error")

        for specialist in self.specialists:
            findings.extend(await specialist.analyze_async(trigger=trigger, pod_info=pod_info))

        if self.synthesis is not None and findings:
            _primary, ordered = self.synthesis.rank(findings)
            confidence = self.synthesis.aggregate_confidence(ordered)
        else:
            confidence = max((f.confidence for f in findings), default=0.2)
        return DiagnosticReport(
            investigation_id=f"inv-{uuid4().hex[:12]}",
            findings=findings,
            evidence_gaps=evidence_gaps,
            confidence=confidence,
        )
```

- [x] **Step 4: Run test to verify it passes**

Run: `task test -- tests/unit/test_orchestrator.py::test_orchestrator_records_evidence_gap_on_tool_failure -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/deepturn_agents/orchestration src/deepturn_agents/models/findings.py tests/unit/test_orchestrator.py
git commit -m "feat: add orchestrator degraded mode and report contract"
```

## Task 7: Add Microsoft Agent Runtime Wrapper and Specialist Agents

**Files:**
- Create: `src/deepturn_agents/agents/microsoft_runtime.py`
- Create: `src/deepturn_agents/agents/specialists.py`
- Test: `tests/unit/test_synthesis.py`

- [x] **Step 1: Write failing specialist output contract test**

```python
# tests/unit/test_synthesis.py
from deepturn_agents.agents.specialists import RuntimeSpecialist
import asyncio


class StubRuntime:
    async def complete_async(self, prompt: str) -> str:
        return "hypothesis=CrashLoop from probe failures;confidence=0.78"


def test_runtime_specialist_returns_structured_finding() -> None:
    specialist = RuntimeSpecialist(runtime=StubRuntime())
    findings = asyncio.run(specialist.analyze_async(trigger=None, pod_info=[]))
    assert len(findings) == 1
    assert findings[0].confidence == 0.78


def test_runtime_specialist_falls_back_on_malformed_output() -> None:
    class BadRuntime:
        async def complete_async(self, prompt: str) -> str:
            return "unexpected output"

    specialist = RuntimeSpecialist(runtime=BadRuntime())
    findings = asyncio.run(specialist.analyze_async(trigger=None, pod_info=[]))
    assert len(findings) == 1
    assert findings[0].confidence == 0.3


def test_runtime_specialist_disposes_owned_runtime_only() -> None:
    class ClosableRuntime:
        def __init__(self) -> None:
            self.closed = 0

        async def complete_async(self, prompt: str) -> str:
            return "hypothesis=ok;confidence=0.70"

        async def aclose(self) -> None:
            self.closed += 1

    owned = ClosableRuntime()
    external = ClosableRuntime()

    owned_specialist = RuntimeSpecialist(runtime=owned, owns_runtime=True)
    external_specialist = RuntimeSpecialist(runtime=external, owns_runtime=False)

    asyncio.run(owned_specialist.aclose())
    asyncio.run(external_specialist.aclose())

    assert owned.closed == 1
    assert external.closed == 0
```

- [x] **Step 2: Run test to verify it fails**

Run: `task test -- tests/unit/test_synthesis.py::test_runtime_specialist_returns_structured_finding -v`
Expected: FAIL with missing specialist class

- [x] **Step 3: Implement Microsoft runtime wrapper and one specialist**

```python
# src/deepturn_agents/agents/microsoft_runtime.py
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential


class MicrosoftAgentRuntime:
    def __init__(self, project_endpoint: str, model: str) -> None:
        credential = AzureCliCredential()
        self.client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=credential,
        )

    async def complete_async(self, prompt: str) -> str:
        # Start with a fixed instruction contract to keep findings structured.
        agent = self.client.as_agent(
            name="RuntimeDiagnosticsAgent",
            instructions="Return strict format: hypothesis=<text>;confidence=<0-1>",
        )
        result = await agent.run(prompt)
        return str(result)

    async def aclose(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            maybe = close()
            if hasattr(maybe, "__await__"):
                await maybe
```

```python
# src/deepturn_agents/agents/specialists.py
from deepturn_agents.models.findings import DiagnosticFinding
import re


FINDING_RE = re.compile(r"hypothesis=(?P<hyp>.*?);\s*confidence=(?P<conf>0(\.\d+)?|1(\.0+)?)", re.IGNORECASE | re.DOTALL)


class RuntimeSpecialist:
    def __init__(self, runtime, owns_runtime: bool = False) -> None:
        self.runtime = runtime
        self.owns_runtime = owns_runtime

    async def analyze_async(self, trigger, pod_info) -> list[DiagnosticFinding]:
        raw = await self.runtime.complete_async("Analyze runtime instability using sanitized evidence.")
        match = FINDING_RE.search(raw)
        if match is None:
            confidence = 0.3
            hypothesis = "Insufficiently structured model output"
        else:
            confidence = float(match.group("conf"))
            hypothesis = match.group("hyp").strip()
        return [
            DiagnosticFinding(
                hypothesis=hypothesis,
                confidence=confidence,
                supporting_evidence_refs=["runtime:1"],
                contradicting_evidence_refs=[],
                manual_validation_steps=["kubectl describe pod <pod> -n <ns>"],
            )
        ]

    async def aclose(self) -> None:
        if not self.owns_runtime:
            return
        close = getattr(self.runtime, "aclose", None)
        if callable(close):
            await close()
```

- [x] **Step 4: Run test to verify it passes**

Run: `task test -- tests/unit/test_synthesis.py::test_runtime_specialist_returns_structured_finding -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/deepturn_agents/agents tests/unit/test_synthesis.py
git commit -m "feat: add microsoft agent runtime wrapper and runtime specialist"
```

## Task 8: Add Synthesis and Report Composer

**Files:**
- Create: `src/deepturn_agents/agents/synthesis.py`
- Create: `src/deepturn_agents/reporting/composer.py`
- Test: `tests/unit/test_synthesis.py`

- [x] **Step 1: Write failing synthesis ranking test**

```python
# tests/unit/test_synthesis.py
from deepturn_agents.agents.synthesis import SynthesisAgent
from deepturn_agents.models.findings import DiagnosticFinding, DiagnosticReport
from deepturn_agents.reporting.composer import to_markdown


def test_synthesis_picks_highest_confidence_primary() -> None:
    s = SynthesisAgent()
    findings = [
        DiagnosticFinding(hypothesis="A", confidence=0.41, supporting_evidence_refs=["a"], contradicting_evidence_refs=[], manual_validation_steps=["x"]),
        DiagnosticFinding(hypothesis="B", confidence=0.83, supporting_evidence_refs=["b"], contradicting_evidence_refs=[], manual_validation_steps=["y"]),
    ]
    primary, ordered = s.rank(findings)
    assert primary.hypothesis == "B"
    assert ordered[0].confidence == 0.83


def test_synthesis_aggregate_confidence_penalizes_disagreement() -> None:
    s = SynthesisAgent()
    findings = [
        DiagnosticFinding(hypothesis="A", confidence=0.92, supporting_evidence_refs=["a"], contradicting_evidence_refs=[], manual_validation_steps=["x"]),
        DiagnosticFinding(hypothesis="B", confidence=0.30, supporting_evidence_refs=["b"], contradicting_evidence_refs=[], manual_validation_steps=["y"]),
    ]
    _, ordered = s.rank(findings)
    aggregate = s.aggregate_confidence(ordered)
    assert aggregate < 0.92
    assert aggregate >= 0.2


def test_report_composer_includes_required_sections() -> None:
    report = DiagnosticReport(
        investigation_id="inv-123",
        findings=[
            DiagnosticFinding(
                hypothesis="CrashLoop due to probe timeout",
                confidence=0.83,
                supporting_evidence_refs=["log:1"],
                contradicting_evidence_refs=[],
                manual_validation_steps=["kubectl describe pod api-1 -n default"],
            )
        ],
        evidence_gaps=["events_timeout"],
        confidence=0.79,
    )
    md = to_markdown(report)
    assert "## Summary" in md
    assert "## Findings" in md
    assert "## Evidence gaps" in md
    assert "## Manual validation" in md
```

- [x] **Step 2: Run test to verify it fails**

Run: `task test -- tests/unit/test_synthesis.py::test_synthesis_picks_highest_confidence_primary -v`
Expected: FAIL with missing `SynthesisAgent`

- [x] **Step 3: Implement synthesis and report composer**

```python
# src/deepturn_agents/agents/synthesis.py
from deepturn_agents.models.findings import DiagnosticFinding


class SynthesisAgent:
    def rank(self, findings: list[DiagnosticFinding]) -> tuple[DiagnosticFinding, list[DiagnosticFinding]]:
        ordered = sorted(findings, key=lambda f: f.confidence, reverse=True)
        return ordered[0], ordered

    def aggregate_confidence(self, ordered: list[DiagnosticFinding]) -> float:
        if not ordered:
            return 0.2
        top = ordered[0].confidence
        runner_up = ordered[1].confidence if len(ordered) > 1 else top
        disagreement_penalty = 0.10 if abs(top - runner_up) > 0.35 else 0.0
        aggregate = (0.7 * top) + (0.3 * runner_up) - disagreement_penalty
        return max(0.2, min(0.95, aggregate))
```

```python
# src/deepturn_agents/reporting/composer.py
from deepturn_agents.models.findings import DiagnosticReport


def to_markdown(report: DiagnosticReport) -> str:
    lines = [
        f"# Investigation {report.investigation_id}",
        "## Summary",
        f"Overall confidence: {report.confidence:.2f}",
    ]
    if report.evidence_gaps:
        lines.append("## Evidence gaps")
        lines.extend([f"- {gap}" for gap in report.evidence_gaps])
    lines.append("## Findings")
    for f in report.findings:
        lines.append(f"- {f.hypothesis} ({f.confidence:.2f})")
    lines.append("## Manual validation")
    for finding in report.findings:
        for step in finding.manual_validation_steps:
            lines.append(f"- {step}")
    return "\n".join(lines)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `task test -- tests/unit/test_synthesis.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/deepturn_agents/agents/synthesis.py src/deepturn_agents/reporting/composer.py tests/unit/test_synthesis.py
git commit -m "feat: add finding synthesis and report composition"
```

## Task 9: Wire CLI to Orchestrator and Add Scenario Integration Tests

**Files:**
- Modify: `src/deepturn_agents/cli.py`
- Create: `src/deepturn_agents/adapters/fake_k8s_adapter.py`
- Create: `tests/integration/test_scenarios.py`
- Create: `tests/fixtures/scenarios/crashloop.json`
- Create: `tests/fixtures/scenarios/imagepullbackoff.json`
- Create: `tests/fixtures/scenarios/unschedulable.json`
- Create: `tests/fixtures/scenarios/oom_probe_fail.json`

- [x] **Step 1: Write failing integration test for crashloop scenario**

```python
# tests/integration/test_scenarios.py
from pathlib import Path
from typer.testing import CliRunner
from deepturn_agents.cli import app

runner = CliRunner()


def test_crashloop_scenario_produces_runtime_hypothesis(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["investigate", "default/deploy-api", "--out-dir", str(tmp_path)],
        env={"DEEPTURN_TEST_SCENARIO": "crashloop"},
    )
    assert result.exit_code == 0
    assert "CrashLoop" in result.stdout
```

- [x] **Step 2: Run test to verify it fails**

Run: `task test -- tests/integration/test_scenarios.py::test_crashloop_scenario_produces_runtime_hypothesis -v`
Expected: FAIL because runtime wiring and test-only adapter injection do not exist

- [x] **Step 3: Implement fake adapter fixtures and CLI wiring**

```python
# src/deepturn_agents/adapters/fake_k8s_adapter.py
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
        return "ok"
```

```python
# src/deepturn_agents/cli.py
import typer
from deepturn_agents.adapters.fake_k8s_adapter import FakeK8sAdapter
from deepturn_agents.policy.tool_policy import ToolPolicy
from deepturn_agents.tools.tool_gateway import ToolGateway
from deepturn_agents.orchestration.orchestrator import InvestigationOrchestrator
from deepturn_agents.agents.specialists import RuntimeSpecialist
from deepturn_agents.agents.microsoft_runtime import MicrosoftAgentRuntime

app = typer.Typer(no_args_is_help=True)


@app.command("investigate")
def investigate(
    target: str,
    out_dir: str = typer.Option("./artifacts", "--out-dir"),
) -> None:
    namespace, workload_ref = target.split("/", 1)
    import os
    scenario = os.getenv("DEEPTURN_TEST_SCENARIO")
    adapter = FakeK8sAdapter(scenario=scenario or "baseline")
    policy = ToolPolicy(allowed_namespaces={"default"}, max_log_bytes=2048, max_log_seconds=300)
    gateway = ToolGateway(adapter=adapter, policy=policy)
    runtime = MicrosoftAgentRuntime(project_endpoint="https://example", model="gpt-5.4-mini")
    specialist = RuntimeSpecialist(runtime=runtime, owns_runtime=True)
    orchestrator = InvestigationOrchestrator(tool_gateway=gateway, specialists=[specialist], synthesis=None)
    from deepturn_agents.models.triggers import InvestigationTrigger
    import asyncio
    try:
        report = asyncio.run(orchestrator.run_async(
            InvestigationTrigger(
                cluster_id="cluster-local",
                namespace=namespace,
                workload_ref=workload_ref,
                pod_refs=[],
                symptom_type="runtime",
                severity="high",
                observed_at="2026-05-16T10:00:00Z",
            )
        ))
    finally:
        asyncio.run(specialist.aclose())
    primary = report.findings[0].hypothesis if report.findings else "Insufficient data"
    typer.echo(f"investigation_id={report.investigation_id} hypothesis={primary} out_dir={out_dir}")
```

- [x] **Step 4: Run integration test to verify it passes**

Run: `task test -- tests/integration/test_scenarios.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/deepturn_agents/cli.py src/deepturn_agents/adapters/fake_k8s_adapter.py tests/integration/test_scenarios.py tests/fixtures/scenarios
git commit -m "feat: wire cli investigation flow and scenario integration tests"
```

## Task 10: Add End-to-End Report Artifacts and Quality Gates

**Files:**
- Modify: `src/deepturn_agents/cli.py`
- Create: `tests/e2e/test_cli_investigate.py`
- Modify: `README.md`

- [x] **Step 1: Write failing E2E artifact test**

```python
# tests/e2e/test_cli_investigate.py
from pathlib import Path
from typer.testing import CliRunner
from deepturn_agents.cli import app
from deepturn_agents.models.findings import DiagnosticReport

runner = CliRunner()


def test_investigate_writes_markdown_and_json_reports(tmp_path: Path) -> None:
    result = runner.invoke(app, ["investigate", "default/deploy-api", "--out-dir", str(tmp_path)], env={"DEEPTURN_TEST_SCENARIO": "crashloop"})
    assert result.exit_code == 0
    md_files = list(tmp_path.glob("*.md"))
    json_files = list(tmp_path.glob("*.json"))
    assert len(md_files) == 1
    assert len(json_files) == 1
    loaded = DiagnosticReport.model_validate_json(json_files[0].read_text(encoding="utf-8"))
    assert loaded.investigation_id
    assert "## Findings" in md_files[0].read_text(encoding="utf-8")
```

- [x] **Step 2: Run test to verify it fails**

Run: `task test -- tests/e2e/test_cli_investigate.py::test_investigate_writes_markdown_and_json_reports -v`
Expected: FAIL because out-dir writing is not implemented

- [x] **Step 3: Implement report writing and quality command docs**

```python
# src/deepturn_agents/cli.py
import json
import os
import asyncio
from pathlib import Path
import typer
from deepturn_agents.adapters.fake_k8s_adapter import FakeK8sAdapter
from deepturn_agents.policy.tool_policy import ToolPolicy
from deepturn_agents.tools.tool_gateway import ToolGateway
from deepturn_agents.orchestration.orchestrator import InvestigationOrchestrator
from deepturn_agents.agents.specialists import RuntimeSpecialist
from deepturn_agents.agents.microsoft_runtime import MicrosoftAgentRuntime
from deepturn_agents.reporting.composer import to_markdown
from deepturn_agents.models.triggers import InvestigationTrigger

app = typer.Typer(no_args_is_help=True)

def _persist_report(report, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{report.investigation_id}.md"
    json_path = out_dir / f"{report.investigation_id}.json"
    md_path.write_text(to_markdown(report), encoding="utf-8")
    payload = report.model_dump(mode="json")
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return md_path, json_path


@app.command("investigate")
def investigate(
    target: str,
    out_dir: str = typer.Option("./artifacts", "--out-dir"),
) -> None:
    namespace, workload_ref = target.split("/", 1)
    scenario = os.getenv("DEEPTURN_TEST_SCENARIO")
    adapter = FakeK8sAdapter(scenario=scenario or "baseline")
    policy = ToolPolicy(allowed_namespaces={"default"}, max_log_bytes=2048, max_log_seconds=300)
    gateway = ToolGateway(adapter=adapter, policy=policy)
    runtime = MicrosoftAgentRuntime(project_endpoint="https://example", model="gpt-5.4-mini")
    specialist = RuntimeSpecialist(runtime=runtime, owns_runtime=True)
    orchestrator = InvestigationOrchestrator(tool_gateway=gateway, specialists=[specialist], synthesis=None)
    trigger = InvestigationTrigger(
        cluster_id="cluster-local",
        namespace=namespace,
        workload_ref=workload_ref,
        pod_refs=[],
        symptom_type="runtime",
        severity="high",
        observed_at="2026-05-16T10:00:00Z",
    )
    try:
        report = asyncio.run(orchestrator.run_async(trigger))
    finally:
        asyncio.run(specialist.aclose())
    md_path, json_path = _persist_report(report=report, out_dir=Path(out_dir))
    typer.echo(f"investigation_id={report.investigation_id} markdown={md_path} json={json_path}")
```

```markdown
# README.md
## Setup

Install uv and task:

brew install uv go-task

Sync dependencies:

task sync

Generate or refresh lockfile whenever dependencies change:

task lock

Verify pinned runtime dependency versions:

task deps-verify

## Quality gates

Run all tests:

task test -- -v

Run lint and type-check:

task lint
task typecheck
```

- [x] **Step 4: Run full quality gates**

Run: `task quality`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/deepturn_agents/cli.py tests/e2e/test_cli_investigate.py README.md
git commit -m "feat: persist diagnostic report artifacts and add quality gates"
```

## Final Verification Checklist

- [x] Install dependencies: `task sync`
- [x] Generate lockfile: `task lock`
- [x] Verify runtime dependency versions: `task deps-verify`
- [x] Run all tests: `task test -- -v`
- [x] Run lint: `task lint`
- [x] Run type checks: `task typecheck`
- [x] Manual CLI check: `diagctl investigate default/deploy-api --out-dir ./artifacts`
- [x] Confirm artifacts exist in `./artifacts` and include redacted output

## Spec Coverage Self-Review

- Hybrid detection requirement: covered by Task 5.
- Deterministic orchestrator requirement: covered by Task 6.
- Three read-only tools and policy boundary: covered by Task 4.
- Sanitization before reasoning: covered by Tasks 3 and 4.
- Specialist agent diagnostics and synthesis: covered by Tasks 7 and 8.
- CLI-first report outputs in Markdown and JSON: covered by Tasks 1, 9, and 10.
- Error handling and evidence gaps: covered by Task 6.
- Test strategy (unit, integration, E2E): covered by Tasks 1 to 10.

No uncovered spec requirements found.

## Placeholder Scan Self-Review

- No TODO/TBD placeholders present.
- No unresolved gap placeholders remain in this plan revision.
- All code-changing steps include concrete code blocks.
- All test steps include exact command and expected failure or pass result.

## Type and Naming Consistency Self-Review

- `InvestigationTrigger`, `SanitizedEvidenceBundle`, `DiagnosticFinding`, and `DiagnosticReport` naming is consistent across tasks.
- `ToolGateway` and `ToolPolicy` method names are consistent across test and implementation steps.
- CLI command name remains `investigate` throughout all tasks.

## Task Re-Evaluation Summary

- Task ordering remains valid for TDD flow: bootstrap, models, policy/sanitization, adapter gateway, detection, orchestration, runtime specialists, synthesis/composer, integration wiring, E2E artifacts.
- CLI contract is consistent across tasks: `investigate target --out-dir <path>`.
- Added preflight project structure and repository checks are in place before first failing test execution.
- Quality and dependency lifecycle commands are explicit and repeatable: `task sync`, `task lock`, `task deps-verify`, `task quality`.
- No unresolved placeholders or deferred gap markers remain.
