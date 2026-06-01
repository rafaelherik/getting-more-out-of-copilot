# Getting More out of Copilot — Agent Mode, Context & Memory

> Companion materials for the talk **“Getting More out of Copilot”**, delivered at the
> **Community of Practice — Schiphol**.

This repository contains everything you need to follow along with — or re-run — the
session after the talk. If you saw the presentation live, this is where you pick up the
slides, the working code that was built on stage, and the full agent "flight recording"
of how it came together.

---

## Who this is for

- **Attendees** of the session who want to replay the slides and dig into the example.
- **Anyone** curious how a mid-range model plus disciplined workflow produces
  production-shaped code — the central argument of the talk.

No prior exposure to the talk is required. Start with the slides, then open the code.

---

## What's in this repository

| Folder | What it is |
| --- | --- |
| [`presentation/`](./presentation) | The interactive slide deck — a self-contained, airport-themed web app you open in a browser. |
| [`code/`](./code) | `deepturn-agents`: the live example built during the talk — a CLI-first, agentic Kubernetes diagnostics prototype (Python + Microsoft Agent Framework). |
| [`session-transcript/`](./session-transcript) | The agent **flight recording** — the captured session of building the example, start to finish. |

---

## The talk in five takeaways

The session walks through Copilot Agent Mode end to end, framed as a journey through an
airport — check-in, orientation, the work itself, security, and departure. The five
things to take with you:

1. **Agent Mode is the unlock** — Plan → Agent. Permissions scope autonomy.
2. **Plugins multiply capability** — Superpowers: brainstorm → execute.
3. **Mid-range models are enough** — Structure beats raw model size.
4. **Manage context actively** — `/clear`, compaction, and `AGENTS.md`.
5. **Auto-approve the boring stuff** — Safe, idempotent commands at the workspace level.

The thread connecting all five: *fixing a bad plan costs minutes; fixing bad code costs
hours.* The workflow — brainstorm, plan, red-team the plan, then build test-first — is
what makes a smaller model reliable.

---

## The running example: `deepturn-agents`

The talk builds a real tool on stage: an agentic Kubernetes diagnostics CLI with
specialized agents and tools that read cluster state. A key design constraint —
demonstrated live — is that the data shared with agents **does not contain PII**:
secrets, bearer tokens, and JWTs are redacted before they ever reach a model.

You can run it yourself. See [`code/README.md`](./code/README.md) for full setup, but the
short version:

```bash
# from ./code
brew install uv go-task
task sync               # install dependencies
task scenario:all       # run every dummy diagnostic scenario
task test -- -v         # run the test suite
```

The investigation outputs land in [`code/artifacts/`](./code/artifacts), grouped by
scenario (`crashloop`, `imagepullbackoff`, `unschedulable`, `oom_probe_fail`). Each
investigation produces a sanitized Markdown report plus its underlying JSON.

---

## Running the presentation

The deck is a pre-built static web app — no build step required.

```bash
# from ./presentation, serve the folder over HTTP, e.g.:
python3 -m http.server 8080
# then open http://localhost:8080
```

> Opening `presentation/index.html` directly via `file://` may not work because the app
> loads its JavaScript and CSS as ES modules; serving over HTTP avoids that. 

---

## How to use these materials

1. **Watch / replay the slides** in `presentation/` to get the narrative.
2. **Read the flight recording** in `session-transcript/` to see the exact agent session
   — every decision, plan, and red-team pass — that produced the example.
3. **Run the code** in `code/` to see the diagnostics tool work for yourself.

---

