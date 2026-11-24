# Classification

Classification maps an input — issue state (`OPEN` or `CLOSED`) and label set —
to three results:

| Result | Derivation | Question |
|---|---|---|
| mode | `modeResult` | Is this a gate issue, a legacy issue, an issue without mode, or a conflict? |
| contract | `contractResult` | Is a gate issue valid, and what are its type, top gate, maturity, exec, holds, terminal state and role? |
| pool | `poolResult` | Which claim pool is contractually admissible? |

All three are defined as data in `derivations`, evaluated in the listed order.

## Decision tables

A derivation is either an expression (`expr`) or an ordered decision table
(`rows`). In a table the **first row whose `when` holds wins**; the last row is
always a default row (`{"always": true}`).

A row result is one of:

- `value` — a value expression (for simple derived values),
- `ok` — a result object whose fields are value expressions,
- `fail` — `class`, `reason`, `handoff`,
- `propagate` — the result of an earlier derivation, unchanged.

## Condition language

Defined in `schema/gate-model.schema.json` (`$defs/condition`):

| Condition | Meaning |
|---|---|
| `has` | a label is present |
| `count` | number of selected label occurrences compared (`eq`, `ne`, `lt`, `le`, `gt`, `ge`) with an integer |
| `duplicates` | some selected label occurs more than once |
| `state` | the issue state is in a list |
| `value` | a derived value is in a list; dotted paths read result fields (`modeResult.outcome`); a missing path is false |
| `sameValue` | two derived values are equal |
| `ref` | a named base condition (transitions only) |
| `always` | true |
| `all`, `any`, `not` | combinators |

Selectors pick labels by family (`members`: `all`, `known`, `unknown`), by an
explicit list, by the named set `legacyStatuses`, or as a union (`anyOf`).
Labels are counted per occurrence. A GitHub label set has no duplicates; only
artificial evaluator inputs (`inputKind: "evaluator-sequence"`) do.

Value expressions: `literal`, `ref`, `suffix` (suffix of the single member of a
family), `highestPresent` (suffix of the highest present gate of the type's
chain), `joinPresent` (present labels in fixed order), `joinSuffixes` (sorted
suffixes).

The tables need no prose to evaluate. A conforming interpreter is all a consumer
needs; this repository does not ship one.

## Mode (G1)

Rows in order: unknown `mode:*` → `unknown-mode-label`; `mode:gate` more than
once → `marker-duplicate`; with `mode:gate`: a work status →
`gate-with-work-status`, two terminals → `terminal-multiple`, `role:planner` →
`gate-with-legacy-role`, otherwise `ok mode=gate`. Without marker: gate
vocabulary → `gate-vocab-without-marker`; no status but a role →
`role-without-status`; no status → `ok mode=none`; several statuses →
`legacy-status-multiple`; an unknown status → `legacy-status-unknown`;
otherwise `ok mode=legacy`.

Every mode conflict has handoff `comment-only`: no workflow write at all.

## Contract (G1, G2, G7, G8)

A mode failure propagates. Legacy and no-mode issues give `not-gate-mode`
(`mode-legacy`, `mode-none`, handoff `none`). For gate issues, in order:

1. **Prefix** (`prefix-invalid`, handoff `needs-operator`): `unknown-gate`,
   `type-gate-mismatch`, `prefix-gap`, `missing-created`.
2. **Cardinality** (`cardinality-invalid`, handoff `comment-only`):
   `duplicate-label`, `maturity-multiple`, `maturity-unknown`,
   `maturity-missing`, `exec-on-parent`, `exec-multiple`, `exec-unknown`,
   `exec-missing`, `terminal-with-role`.
3. Otherwise `ok` with `type`, `top`, `maturity`, `exec`, `holds`, `terminal`,
   `roleExpected`, `roleActual`, `roleDrift`.

**Terminal state:** `final` (CLOSED with one terminal), `open-recovery` (OPEN
with terminal: operator recovery, no agent work), `closed-pending` (CLOSED
without terminal: legal short-lived state after a merge), `none`.

**Role projection** (`roleExpected`, precedence top to bottom): terminal →
none; `needs:replanning` → architect; `created`/`drafted` → architect;
`specified` → operator; parent `activated` → operator; task `promoted` with
`exec:agent` → coder; with `exec:operator` → operator; `implemented` → reviewer;
`accepted` → operator; otherwise none. `needs:operator` and `needs:upstream`
leave the projection unchanged.

**Role drift** (`roleDrift`) compares the projection with the present roles. It
is a diagnosis, never an error, and never a claim permission.

## Claim pool (G3, G4, G6)

A contract failure propagates. Otherwise: not OPEN → none; terminal → none;
`needs:operator` or `needs:upstream` → none; `needs:replanning` → `re-spec`;
`created` → `draft`; `drafted` → `co-arch`; `specified` → `operator-wait`; task
`promoted` with `exec:agent` → `dev`, with `exec:operator` → `operator-wait`;
`implemented` → `qat`; otherwise none. `minMaturity` is `master` for the
`draft` pool without maturity, else `none`.

A pool is a static statement about admissibility. Capability, claim slots,
leases, the main architect's identity and the quorum are external
(`claimPools.ruleTextOnly`, `externalPreconditions`).

## Action guard (consumer safety)

`actionGuard` is a fourth result, independent of the other three and without
evaluator counterpart. It fails with `consumer-guard` / `unknown-hold` (handoff
`comment-only`) as soon as any unknown `needs:*` label is present, otherwise it
is `ok` (`guard: pass`). A consumer offers no write and no claim unless it is
`ok`; every transition requires it through `transitions.globalPrecheck`.

## Result format and serialization

Results are objects. For a mechanical comparison with the line format of the
agent-loop evaluator:

| Model field | Evaluator key |
|---|---|
| `outcome` | leading `ok` / `fail` |
| `class`, `reason`, `handoff` | `class=`, `reason=`, `handoff=` |
| `mode` | `mode=` |
| `type`, `top`, `maturity`, `exec`, `holds`, `terminal` | same names |
| `roleExpected`, `roleActual`, `roleDrift` | `role_expected=`, `role_actual=`, `role_drift=` |
| `pool`, `minMaturity`, `hold` | `pool=`, `min_maturity=`, `hold=` |

`holds` / `hold`: present holds in the order `needs:operator`,
`needs:replanning`, `needs:upstream`, joined with `,`; `none` if empty.
`roleActual`: suffixes of all `role:*` labels sorted by code point, joined with
`+`; `none` if empty. `roleActual` echoes input and is not an output code.
