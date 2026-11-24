# Transitions

`transitions.items` lists every label transition of a gate issue. Each one
states:

| Field | Meaning |
|---|---|
| `kind` | create, gate set/withdraw, hold set/release, terminal set, maturity or exec change, recovery |
| `actors`, `operatorOnly` | who may perform it |
| `labelChanges` | labels added, removed or replaced; `operatorDefined` for recovery |
| `cascade` | for withdrawals: removal order, highest gate first |
| `staticPrecheck` | from which classification results the transition is admissible (a condition) |
| `exceptions` | admitted deviations from the regular pre-check (G7 terminal, recovery) |
| `externalPreconditions` | what labels cannot prove, by name (catalogue in `externalPreconditions.catalog`) |
| `postWrite` | mandatory steps after the write: role projection, readback, remove roles, close issue |

## Static pre-check is not authorisation

A matching `staticPrecheck` is **at most a necessary static pre-check**. It is
never authorisation and never proof of actor, provenance, live claims, quorum,
current head or evidence, or absence of concurrent changes. A consumer offers a
write only after checking the external preconditions through the authoritative
write path. If any of them is unknown, the write is not offered (fail-closed).

No result `ok` anywhere in the model means "allowed to write".

## Overview

| Transition | Actor | Static pre-check (short) | Key external preconditions |
|---|---|---|---|
| `create-gate-issue` | architect, operator | mode none, OPEN | gate-start go, provable creation time |
| `set-drafted` | architect | top created, pool draft/re-spec, one maturity | main architect, draft claim, capability |
| `set-specified` | architect | top drafted, pool co-arch/re-spec | main architect, co-arch quorum |
| `set-promoted` | operator only | task, top specified, no hold, one exec | operator identity |
| `set-activated` | operator only | parent, top specified, no hold | operator identity |
| `set-implemented-agent` | coder | pool dev | dev claim, submitted delivery |
| `set-implemented-operator` | operator only | task, top promoted, exec operator, no hold | operator identity, evidence |
| `set-accepted` | reviewer | pool qat | QAT claim, independent reviewer, same head |
| `withdraw-delivery` | reviewer, coder | task, top implemented/accepted | QAT claim released first |
| `withdraw-specified` | architect | top at or above specified | affected claims halted first |
| `withdraw-promoted-for-exec-change` | operator only | task, top at or above promoted | claims halted first |
| `change-maturity` | architect | top created/drafted | main architect |
| `set-exec` | architect, operator | task, top below promoted | — beyond concurrency |
| `set-hold-replanning` | reviewer, operator | contract ok, OPEN, no terminal | documented reason |
| `release-hold-replanning` | architect | top specified again | quorum of the current round |
| `set-hold-operator` | any | contract ok — **exception:** prefix-invalid | documented reason |
| `release-hold-operator` | operator only | contract ok | operator identity |
| `set-hold-upstream` | any | contract ok | documented reason |
| `release-hold-upstream` | operator only | contract ok | proven fulfilment |
| `set-terminal-finished` | operator only | **G7:** mode gate, no terminal; no gate precondition | all claims released, merge or evidence |
| `set-terminal-abandoned` | operator only | **G7:** mode gate, no terminal | all claims released, deliberate abort |
| `recover-prefix-invalid` | operator only | contract prefix-invalid | operator identity |
| `recover-open-terminal` | operator only | terminal open-recovery | operator identity |

## Rules that shape the table

- **Mode conflict:** no workflow write at all, not even a hold; handoff by
  comment/notify (G1).
- **Prefix invalid:** every interaction stops; the only workflow write is the
  `needs:operator` hold with diagnosis, and recovery belongs to the operator
  (G2). Roles stay unchanged until the prefix is valid (G8).
- **Withdrawals** run top-down. QAT findings remove `accepted` then
  `implemented`; `promoted` stays (G5). Losing `specified` removes `promoted` or
  `activated` and all delivery gates; re-promotion or re-activation is again an
  operator gate (G6).
- **Claims before gates:** a running QAT claim is released before its gate is
  withdrawn or the head changes (G5); affected claims are halted before their
  gate preconditions go (G6).
- **Terminal:** no additional gate precondition, but unambiguous mode, terminal
  uniqueness and release of all claims; if releasing claims fails, the terminal
  write does not happen (G7). An issue with terminal carries no role.
- **Non-atomic writes:** GitHub label operations are not atomic. Every write is
  followed by a readback; there is no compare-and-swap.

Where ADR-010 does not name an actor (who creates gate issues, who sets
`needs:upstream`, who sets `exec:*`, who withdraws `promoted` for an exec
change, who withdraws delivery gates after a head change), the model states its
reading in `note` and the point is listed for the conformance check.

Where the agent-loop write path is stricter than ADR-010, the model follows
ADR-010 and names the difference in `note` as an open point: the write path
lets only the operator remove `gate:promoted` and `gate:activated` (also inside
a withdrawal cascade), and it sets maturity and exec only together with
advancing to `drafted` and `specified` respectively, refusing later changes.
