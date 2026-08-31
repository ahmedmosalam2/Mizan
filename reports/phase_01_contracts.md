# MIZAN — Phase 1 Contracts and Domain Foundations

**Date:** 2026-08-31
**Status:** Complete for the canonical-contract foundation; runtime migration remains a subsequent phase.

## Delivered

- A framework-neutral Pydantic contract layer in `mizan/core/contracts.py`.
- Explicit `TEST`, `SANDBOX`, and `REAL` execution modes.
- Mandatory tenant context, correlation IDs, tool actions, permissions, idempotency keys, timeouts, and classified errors.
- Canonical task, agent, tool, approval, campaign, evaluation, benchmark, and experiment-provenance contracts.
- A validated campaign state machine that rejects illegal transitions.
- Tenant-scoped campaign state and market-budget invariants in `mizan/core/state.py`.
- Typed model, retry, runtime, and benchmark configuration models in `mizan/core/configuration.py`.
- Contract tests covering task versioning, failed-tool error classification, human approval attribution, tenant boundary fields, execution-mode dispatch restrictions, budget validation, and state transitions.

## Design rules now encoded

1. Framework runtimes may not define their own business payloads; they must map to the canonical contracts.
2. Every tool request carries company, campaign, task, agent, execution mode, and idempotency context.
3. A failed tool call requires a classified error rather than an implicit or fabricated success.
4. External channel dispatch is disallowed outside `REAL` mode.
5. Campaign transitions are governed centrally; agents cannot skip compliance or approval states.
6. Benchmark results require experiment provenance (code, model, dataset, task-set, config hash, seed, environment, and trial count).

## Verification

```text
python -m pytest --basetemp D:\Mizan\.pytest-work
17 passed in 2.29s

python -m compileall -q mizan
completed successfully
```

## Deliberately not claimed

- Existing legacy adapters have **not** been converted to the canonical runtime contract yet and still cannot produce official benchmark results.
- The contracts do not make the current host-process code executor a secure sandbox.
- No PostgreSQL migration, RabbitMQ worker, Redis state store, Qdrant index, S3 artifact store, API, or real external deployment was added in this phase.
- No benchmark score, cost, latency, safety, or reliability value was produced or updated.

## Next implementation step

Build the Ramadan AUT workflow around the contracts: tenant-scoped repositories, permissioned tools, persisted approvals and audit events, six executable agents, and a native runtime. Only then should framework adapters be migrated and benchmark execution resumed.
