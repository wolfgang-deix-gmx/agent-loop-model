# Overview

This repository describes the **gate lifecycle** of an issue-driven agent loop
as data. The description is derived from ADR-010 (gate lifecycle, sections
G1–G8); every rule in the model names its ADR-010 section.

## Core ideas

- **GitHub issues and labels are the state.** An issue in gate mode carries
  `mode:gate` from creation on. Its type is fixed: `epic` marks a parent,
  everything else is a task.
- **Gates are true, reached results**, not work statuses and not claims. A task
  climbs `created → drafted → specified → promoted → implemented → accepted`;
  a parent climbs `created → drafted → specified → activated`. Gates form a
  cumulative prefix.
- **Claims are time-limited reservations**, separate from gates. The model
  states which claim pool is contractually admissible; leases, quorum counting
  and identity checks are implementation matters and appear only as rule text.
- **Holds** (`needs:operator`, `needs:upstream`, `needs:replanning`) block
  claims without replacing gates.
- **Terminal exits** (`status:finished`, `status:abandoned`) are set only by the
  operator and are neither gate nor work status.
- **Legacy issues** (the older single-status model) are only *recognised*, so
  that a consumer can show them read-only or filter them out.

## What the model contains

| Section of `gate-model.json` | Content | Doc |
|---|---|---|
| `meta` | version, release status, source commits | [versioning.md](versioning.md) |
| `issueTypes`, `issueStates` | task/parent, OPEN/CLOSED | [labels.md](labels.md) |
| `vocabulary` | set (a): admissible label families and members | [labels.md](labels.md) |
| `legacyStatuses` | set (b): statuses used only for legacy recognition | [labels.md](labels.md) |
| `outputCodes` | set (c): every code a result may contain | [classification.md](classification.md) |
| `cardinality` | per family, type and stage | [labels.md](labels.md) |
| `gateChains` | ordered chains and their invariants | [labels.md](labels.md) |
| `derivations` | ordered decision tables: mode, contract, role projection, claim pool, action guard | [classification.md](classification.md) |
| `claimPools` | pools, hold effects, minimum maturity, rule text | [classification.md](classification.md) |
| `externalPreconditions`, `postWrite`, `transitions` | label transitions with actor, static pre-check, exceptions, external preconditions and post-write steps | [transitions.md](transitions.md) |

How to consume the model safely is described in
[consumer-contract.md](consumer-contract.md); which ADR-010 section each rule
comes from is listed in [provenance.md](provenance.md).

## What the model does not contain

- No reference classifier and no runtime for consumers.
- No write path and no GitHub access.
- No legacy lifecycle beyond recognition.
- No authorisation: a matching static pre-check is never permission to write.

## Normative status

The working state is `1.0.0-draft`, `releaseStatus: unreleased`, not normative.
Prose in `docs/` and rule text in the model explain the tables and are not
normative themselves. A release becomes normative only through a separate,
accepted architecture decision that pins it by tag, commit SHA and SHA-256.
