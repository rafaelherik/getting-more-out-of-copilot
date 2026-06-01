# Agentic Kubernetes Diagnostics Design (v1)

Date: 2026-05-16
Status: Approved design draft
Scope: Single-cluster first, structured for future multi-cluster expansion

## 1. Goals and Non-Goals

### Goals
- Build an autonomous diagnostic application using Microsoft Agent Framework in Python.
- Continuously monitor Kubernetes signals in near real time.
- Trigger multi-step investigations for unhealthy workloads.
- Use specialized agents to diagnose likely root causes.
- Expose only constrained, read-only tools to agents:
  - `get_pod_info`
  - `get_events`
  - `get_logs`
- Ensure data sent to agents is sanitized to remove sensitive and PII-like content.
- Produce operator-safe diagnostic guidance and validation steps.
- Provide CLI-first outputs in human-readable and machine-readable formats.

### Non-Goals (v1)
- No automated remediation against the cluster.
- No write/exec/delete/patch/scale actions.
- No multi-cluster fan-out runtime in v1 (design remains extensible for it).
- No UI dashboard in v1.

## 2. Constraints and Decisions

- Deployment model: single cluster in v1; abstraction points prepared for multi-cluster later.
- Execution mode: passive investigation + manual remediation recommendations only.
- Detection model: hybrid watch streams plus periodic reconciliation.
- Model boundary: in-tenant reasoning only.
- Primary interface: CLI-first.

## 3. Recommended Architecture

Recommended approach: hybrid graph architecture.

- Deterministic control plane handles detection, scoping, evidence collection, and safety enforcement.
- Agent reasoning plane handles interpretation and diagnosis from sanitized evidence bundles.

### 3.1 Deterministic Control Plane
- Detector Engine
- Investigation Orchestrator
- Tool Gateway (policy boundary)
- Sanitization Pipeline
- Report Composer and audit sink

### 3.2 Agent Reasoning Plane
- Specialist Diagnostic Agents:
  - SchedulingAgent
  - RuntimeAgent
  - ImageAgent
  - NetworkAgent
- Synthesis Agent merges findings and resolves conflicts.

Design intent:
- Keep Kubernetes access narrow, auditable, and reproducible.
- Keep agent autonomy focused on reasoning, not privileged operations.

## 4. Component Design

### 4.1 Detector Engine
Purpose:
- Convert cluster watch events and reconciliation checks into normalized triggers.

Inputs:
- Kubernetes watch streams (pods, events, workload status).
- Scheduled reconciliation snapshots.

Outputs:
- `InvestigationTrigger`:
  - `cluster_id`
  - `namespace`
  - `workload_ref`
  - `pod_refs`
  - `symptom_type`
  - `severity`
  - `observed_at`

### 4.2 Investigation Orchestrator
Purpose:
- Execute deterministic investigation workflow state transitions.

Responsibilities:
- Open investigation context with correlation id.
- Apply scope policy.
- Call tools via Tool Gateway only.
- Route sanitized bundle to specialist agents.
- Build final diagnostic report.

### 4.3 Tool Gateway (Critical Safety Boundary)
Purpose:
- Single controlled interface between orchestration and Kubernetes adapters.

Allowed tools:
- `get_pod_info`
- `get_events`
- `get_logs`

Policy checks before execution:
- Namespace/workload allowlist.
- Time-window and byte-count limits.
- Resource count caps.
- Request provenance and audit logging.

Hard denials:
- Any write, patch, delete, exec, or scale action.
- Raw secret retrieval and unconstrained resource dumps.

### 4.4 Sanitization Pipeline
Purpose:
- Transform raw tool data into safe, typed evidence for reasoning.

Pipeline stages:
1. Content classification and field mapping.
2. Sensitive pattern masking (token/key/credential signatures).
3. High-entropy string masking.
4. Truncation and normalization.
5. Provenance and redaction metadata attachment.

Output:
- `SanitizedEvidenceBundle` containing:
  - `PodStateEvidence`
  - `EventTimelineEvidence`
  - `LogExcerptEvidence`
  - redaction stats
  - truncation markers
  - source provenance

### 4.5 Specialist Agents
Purpose:
- Analyze sanitized bundle by domain.

Agents:
- SchedulingAgent: quota pressure, taints/tolerations, unschedulable symptoms.
- RuntimeAgent: crash loops, probes, restart and OOM patterns.
- ImageAgent: image pull/auth/tag and registry issues.
- NetworkAgent: service connectivity and related symptom signatures.

Output contract (`DiagnosticFinding`):
- `hypothesis`
- `confidence`
- `supporting_evidence_refs`
- `contradicting_evidence_refs`
- `manual_validation_steps`

### 4.6 Synthesis Agent and Report Composer
Purpose:
- Rank and merge findings into actionable operator output.

Outputs:
- CLI markdown summary.
- JSON diagnostic artifact.

Report sections:
- Primary diagnosis and confidence.
- Alternative hypotheses.
- Evidence map.
- Step-by-step operator actions.
- Verification commands and expected signals.
- Insufficient evidence notes when confidence is low.

## 5. Investigation Data Flow

1. Detect:
- Hybrid detector emits normalized trigger.

2. Scope:
- Orchestrator resolves allowed investigation boundaries and caps.

3. Collect:
- Gateway executes read-only tool calls within policy.

4. Sanitize:
- Raw results become typed sanitized evidence with provenance.

5. Diagnose:
- Relevant specialist agents produce domain findings.

6. Synthesize:
- Synthesis agent produces ranked conclusions and operator guidance.

7. Output and Audit:
- CLI summary + persisted JSON/Markdown + full audit records.

## 6. Error Handling and Degraded Modes

- Tool timeout or policy denial does not abort the investigation.
- Missing evidence is recorded as `EvidenceGap` and reflected in confidence.
- Conflicting specialist outputs are surfaced, not hidden.
- Watch stream disruption triggers reconciliation-only fallback and health warning.
- Final report must distinguish:
  - confirmed signals
  - inferred hypotheses
  - unknowns requiring manual checks

## 7. Security, Privacy, and Guardrails

- Agents receive sanitized evidence only.
- No direct Kubernetes API credentials are exposed to agents.
- Tool layer enforces least privilege and immutable read-only behavior.
- All data access and transformations are auditable by correlation id.
- Redaction is mandatory before model input.
- If sanitization confidence is low, artifact is withheld and flagged.

## 8. CLI Experience (v1)

CLI commands (design-level):
- `diagctl monitor start`
- `diagctl investigate <workload-or-pod-ref>`
- `diagctl report show <investigation-id>`

CLI output requirements:
- Concise summary at top.
- Clear confidence and evidence references.
- Manual next actions only.
- Path to persisted JSON/Markdown artifacts.

## 9. Testing Strategy

### 9.1 Unit Tests
- Policy engine allow/deny decisions.
- Redaction and entropy masking behavior.
- Evidence schema and truncation logic.

### 9.2 Integration Tests
- Fake Kubernetes adapter fixtures:
  - CrashLoopBackOff
  - ImagePullBackOff
  - Unschedulable
  - OOMKilled and probe failures
- Validate findings, confidence, and recommendation quality.

### 9.3 Contract Tests
- Tool Gateway input/output contracts.
- Sanitized evidence schema stability for agents.

### 9.4 End-to-End CLI Tests
- Trigger-to-report flow.
- Degraded-mode behavior on partial tool failures.
- Audit record completeness.

## 10. Future Multi-Cluster Evolution (Post-v1)

- Introduce cluster adapter registry keyed by `cluster_id`.
- Add central coordinator for routing and policy.
- Preserve investigation bundle schema and specialist agent contracts.
- Add per-cluster health status and backlog handling.

## 11. Acceptance Criteria for v1 Design

- Hybrid detection implemented (watch + reconciliation).
- Investigation workflow executes deterministically.
- Only three read-only tools are callable for data collection.
- Redaction and sanitization occur before any agent reasoning.
- Reports include diagnosis, confidence, evidence links, and manual actions.
- No automated remediation paths exist.
- Unit, integration, contract, and E2E tests are defined and runnable.

## 12. Open Assumptions

- Kubernetes RBAC is preconfigured to minimum required read-only permissions.
- In-tenant model hosting/runtime is available in deployment environment.
- Log/event volume is manageable under configured limits for v1.
