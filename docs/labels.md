# Labels

The model keeps three sets strictly apart:

| Set | Model key | Purpose |
|---|---|---|
| (a) vocabulary | `vocabulary.families` | the admissible gate-mode labels (ADR-010 G8), exact names, no aliases |
| (b) legacy statuses | `legacyStatuses.statuses` | statuses of the older model, used only to recognise legacy issues |
| (c) output codes | `outputCodes` | values a classification result may contain |

Input labels are arbitrary strings. A label in a fixture or in a real issue does
not become vocabulary by appearing there.

## Families (set a)

| Family | Labels | Unknown member |
|---|---|---|
| mode | `mode:gate` | mode conflict `unknown-mode-label` |
| gate | `gate:created`, `gate:drafted`, `gate:specified`, `gate:promoted`, `gate:implemented`, `gate:accepted`, `gate:activated` | `prefix-invalid` / `unknown-gate` (without marker: mode conflict) |
| maturity | `maturity:beginner`, `maturity:advanced`, `maturity:master` | `cardinality-invalid` / `maturity-unknown` (without marker: mode conflict) |
| exec | `exec:agent`, `exec:operator` | `cardinality-invalid` / `exec-unknown` (without marker: mode conflict) |
| hold | `needs:operator`, `needs:upstream`, `needs:replanning` | ignored by classification except for duplicate detection; **blocks every consumer action** via `actionGuard` |
| terminal | `status:finished`, `status:abandoned` | any other `status:*` on a gate issue is a work status: mode conflict `gate-with-work-status` |
| role | `role:architect`, `role:operator`, `role:coder`, `role:reviewer` | `role:planner` is a mode conflict; any other unknown role is only role drift |
| type | `epic` | — |

Labels outside all families are **foreign** and ignored by every rule.

`needs:operator` and `needs:upstream` also exist in the legacy model; alone they
are no mode signal. `needs:replanning`, `gate:*`, `maturity:*` and `exec:*`
without `mode:gate` are a mode conflict (`gate-vocab-without-marker`).

## Legacy statuses (set b)

The sixteen statuses accepted by the legacy helper
(`role_for_status` in the agent-loop label invariant library). A legacy issue
has no `mode:gate`, no gate vocabulary and exactly one of these statuses. The
model contains no legacy semantics.

## Cardinality

On an open gate issue (`cardinality.rules`):

| Family | Rule |
|---|---|
| mode | exactly one, from creation |
| gate | valid prefix of the type's chain |
| maturity | zero or one while only `created` is reached; exactly one from `drafted` on |
| exec | task: zero or one before `promoted`, exactly one from `promoted` on; parent: never |
| holds | each hold zero or one |
| terminal | zero or one, mutually exclusive |
| role | exactly one while non-terminal (**diagnostic only**: a violation is role drift, not an error); none with terminal |

`enforcement: classification` means the contract table rejects a violation;
`enforcement: diagnostic` means it is only reported.

## Gate chains

```text
task:   created → drafted → specified → promoted → implemented → accepted
parent: created → drafted → specified → activated
```

Invariants (`gateChains.invariants`): cumulative prefix; only the next gate may
be added; withdrawal from the highest gate downward; a gate of the wrong type is
invalid; an open gate issue without terminal carries at least `gate:created`.
