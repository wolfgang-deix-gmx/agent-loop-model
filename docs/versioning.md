# Versioning

The model uses [Semantic Versioning](https://semver.org/) from `1.0.0` on.
`meta.modelVersion` carries the model version, `meta.schemaVersion` the version
of the model schema.

| Change | Version |
|---|---|
| A label, code, rule or table row is removed or renamed, or a classification result changes for an existing input | MAJOR |
| A label, code, rule, transition or field is added without changing any existing result | MINOR |
| Wording, documentation, fixtures or metadata change without changing any result | PATCH |

**Additive is not backward-handleable.** A MINOR release may add labels, codes or
combinations an older consumer does not know. A consumer pinned to the older
release treats them as unknown and fails closed (see
[consumer-contract.md](consumer-contract.md)).

## Release states

| `releaseStatus` | `modelVersion` | Normative |
|---|---|---|
| `unreleased` | `X.Y.Z-draft` | no |
| `pre-release` | `X.Y.Z-rc.N` | no; only with an explicit operator go |
| `released` | `X.Y.Z` | only after the cutover decision pins it |

- A release is published as a tag `vX.Y.Z` with the model file as release
  asset and its SHA-256.
- A release is created only after a conformance check of the decision tables
  against the fixtures, the agent-loop evaluator and ADR-010. Open deviations
  block the release.
- Releases are immutable. A correction is a new release.
- Pin only an immutable release, never a branch.

## Current state

`1.0.0-draft`, `unreleased`. No tag, no release.
