# Changelog

All notable changes to the model are recorded here from `1.0.0` on. Versioning
follows [docs/versioning.md](docs/versioning.md).

## Unreleased

Working state `1.0.0-draft`, not normative.

- Model file with vocabulary, legacy status list, output codes, cardinality,
  gate chains, decision tables (mode, contract, role projection, claim pool),
  claim pools, external preconditions and transitions.
- JSON Schemas for the model (including the condition language) and for fixtures.
- Fixtures covering every reason code, gate stage, role projection row, hold,
  terminal state, claim pool, duplicate input and label order.
- Structure and coverage check `tools/check.py`.
