# Provenance

Every rule in `model/gate-model.json` carries an `adr` field naming its ADR-010
section. This page summarises the mapping and the sources the model was written
against.

## Sources

| Source | Revision |
|---|---|
| ADR-010 gate lifecycle (`docs/adr/adr-010-gate-lifecycle.md` in the coordination repository) | `c22a1b1f96d5ca26c80742f7b78b9084cff47029` |
| Agent-loop read-only evaluator (`plans/e6-4/gate-contract.lib.sh`: `gate_mode_classify`, `gate_contract_check`, `gate_claim_pool`) | `75c7cf454e65cf1bbf78012dfe41a7531ce1a3b9` |
| Agent-loop legacy status list (`plans/loop-012s/label-invariant.lib.sh`: `role_for_status`) | `75c7cf454e65cf1bbf78012dfe41a7531ce1a3b9` |

Class and reason codes are taken from the evaluator output. Where ADR-010 and
the evaluator differ, ADR-010 governs. A change of any source before a release
requires a new comparison.

## Rule → ADR-010 section

| Model part | ADR-010 |
|---|---|
| `issueTypes`, `type` derivation | G1 |
| `vocabulary` families | G1, G2, G3, G4, G6, G7, G8 (per family) |
| `legacyStatuses` | G1 |
| `cardinality` | G1, G2, G3, G4, G6, G7, G8 (per rule) |
| `gateChains` and invariants | G1, G2, G5, G6, G7 |
| `modeResult` | G1, G7, G8 |
| `contractResult` prefix rows | G1, G2, G7 |
| `contractResult` cardinality rows | G3, G4, G7, G8 |
| `terminal` | G7 |
| `roleExpected`, `roleActual`, `roleDrift` | G6, G7, G8 |
| `pool`, `minMaturity`, `poolResult` | G3, G4, G5, G6, G7 |
| `claimPools` | G3, G4, G5, G6, G7 |
| `externalPreconditions` | G1, G3–G7, Context, Consequences, Non-goals |
| `postWrite` | G7, G8, Consequences |
| `transitions` | G1–G8 (per transition) |

The row-level mapping is the `adr` field of each row and transition in the model
file itself; this table is only an index.
