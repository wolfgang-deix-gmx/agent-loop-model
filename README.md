# agent-loop-model

> **Status: unreleased, not normative.** This is the working state `1.0.0-draft`.
> Until the cutover decision, ADR-010 (gate lifecycle) remains the authoritative
> source. Do not pin this branch; pin only an immutable release (see
> [docs/versioning.md](docs/versioning.md)).

A machine-readable and human-readable description of the **gate lifecycle** used
by an issue-driven agent loop: modes, labels, gate chains, classification,
claim pools and label transitions. It contains **no implementation**: no runtime,
no write path, no GitHub access.

The first consumer is the Agent Loop Control Panel (ALCP).

## Contents

| Path | Content |
|---|---|
| [`model/gate-model.json`](model/gate-model.json) | the model file |
| [`schema/gate-model.schema.json`](schema/gate-model.schema.json) | JSON Schema (Draft 2020-12) of the model, including the condition language |
| [`schema/fixture.schema.json`](schema/fixture.schema.json) | JSON Schema of one fixture |
| [`fixtures/`](fixtures) | example inputs with expected classification |
| [`docs/`](docs) | overview, labels, classification, transitions, consumer contract, versioning, provenance |
| [`tools/check.py`](tools/check.py) | structure and coverage check |

Start with [docs/overview.md](docs/overview.md).

## Running the check

Requires Python 3.11 or newer.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r tools/requirements.txt
.venv/bin/python tools/check.py
```

On Windows the interpreter is `.venv\Scripts\python`.

The script validates the model and every fixture against their schemas and
checks internal consistency and coverage. It exits `0` on success and `1` on any
finding.

**Exit 0 attests structure and coverage only.** The script computes no
classification. Whether the decision tables produce the fixture expectations,
whether those match the agent-loop evaluator, and whether the tables match
ADR-010, is checked separately with a test-only interpreter before a release.

## License

[MIT](LICENSE)
