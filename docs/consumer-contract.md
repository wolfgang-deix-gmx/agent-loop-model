# Consumer contract

Rules for any consumer of this model, for example a control panel.

## 1. Pin an immutable release

- Pin a released version by **tag, tag commit SHA and SHA-256** of the release
  asset `gate-model.json`.
- Never pin a branch, an unreleased working state (`releaseStatus:
  unreleased`) or a version with a pre-release suffix for normative use.
- A checksum protects only if the expected value is bound to a trusted release.
  If the asset is missing, changed or its checksum does not match, **fail** —
  never fall back to another version.

## 2. Fail closed on anything unknown

- An unknown `schemaVersion`, an unknown top-level key relevant to you, an
  unknown condition or expression type, or an unknown output code is an error.
- Content added in a later MINOR release stays unknown to a consumer pinned to
  an older release and must be treated fail-closed there. "Additive" does not
  promise that old consumers can handle new combinations.
- Input labels outside all families are foreign and ignored; unknown members of
  a family are classified by the tables, not guessed.
- **Action guard (mandatory).** Evaluate the derivation `actionGuard` before any
  action. While it is not `ok`, offer no write and no claim, whatever the other
  results say. It fails (`consumer-guard` / `unknown-hold`) for every unknown
  `needs:*` label: such a label may be a hold added in a later model version.
  Classification keeps ignoring unknown holds for diagnosis, compatible with the
  agent-loop evaluator, so a `draft` or `dev` pool can appear beside a blocked
  guard (fixtures `unknown-hold-ignored`, `unknown-hold-blocks-dev-pool`).
  `transitions.globalPrecheck` encodes the same rule for every transition.

## 3. Legacy issues are read-only

The model only recognises legacy issues (`mode: legacy`). A consumer shows them
read-only or filters them out. It offers no transition on them and derives no
role from gate labels on them.

## 4. Static pre-check is not authorisation

- A classification result `ok` and a matching transition `staticPrecheck` are at
  most a necessary static pre-check.
- Before offering a write, the consumer checks every `externalPreconditions`
  entry of the transition through the authoritative write path: provenance and
  identity, claims, quorum, current head or evidence, concurrent changes,
  readback.
- If any external precondition is unknown, the write is not offered.
- Under a mode conflict, no workflow write is offered at all.

## 5. Evaluate the tables, not the prose

- Derivations are evaluated in order; in each table the first matching row
  wins.
- Prose in `docs/`, `note` and `description` fields and `ruleTextOnly` entries
  explain the model and are not normative input to the evaluation.

## 6. Normative status

A release becomes normative only through a separate accepted architecture
decision that pins it. Until then, ADR-010 is authoritative; on a contradiction
between this model and ADR-010, ADR-010 wins.
