# deepturn-agents

CLI-first Kubernetes diagnostics prototype.

## Setup

Install uv and task:

brew install uv go-task

Sync dependencies:

task sync

Generate or refresh lockfile whenever dependencies change:

task lock

Verify pinned runtime dependency versions:

task deps-verify

## Local scenarios

Run a dummy investigation against one scenario:

task scenario:crashloop
task scenario:imagepullbackoff
task scenario:unschedulable
task scenario:oom-probe-fail

Run all dummy scenarios:

task scenario:all

## Quality gates

Run all tests:

task test -- -v

Run lint and type-check:

task lint
task typecheck
