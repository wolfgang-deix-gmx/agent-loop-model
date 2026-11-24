#!/usr/bin/env python3
"""Structure and coverage check for the agent loop gate model.

Validates model/gate-model.json and fixtures/**/*.json against their JSON
Schemas and checks internal consistency and fixture coverage.

Exit 0 attests STRUCTURE AND COVERAGE ONLY. This script computes no
classification and therefore proves no semantic conformance of the decision
tables with the fixture expectations, the agent-loop evaluator or ADR-010.
"""
from __future__ import annotations

import collections
import copy
import json
import pathlib
import sys

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.stderr.write("jsonschema is missing: pip install -r tools/requirements.txt\n")
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parent.parent
G8_PREFIXES = {"mode:", "gate:", "maturity:", "exec:", "needs:", "status:", "role:"}
# Independent reference: the label table of ADR-010 G8, copied by hand.
G8_VOCABULARY = {
    "mode": {"mode:gate"},
    "gate": {"gate:created", "gate:drafted", "gate:specified", "gate:promoted", "gate:implemented",
             "gate:accepted", "gate:activated"},
    "maturity": {"maturity:beginner", "maturity:advanced", "maturity:master"},
    "exec": {"exec:agent", "exec:operator"},
    "hold": {"needs:operator", "needs:upstream", "needs:replanning"},
    "terminal": {"status:finished", "status:abandoned"},
    "role": {"role:architect", "role:operator", "role:coder", "role:reviewer"},
    "type": {"epic"},
}
DISCLAIMER = ("NOTE: exit 0 attests structure and coverage only. No classification was computed; "
              "semantic conformance is checked separately (E8-2).")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.passed: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        if ok:
            self.passed.append(label)
            print(f"PASS  {label}")
        else:
            self.errors.append(f"{label}: {detail}")
            print(f"FAIL  {label}: {detail}")


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk(node, visit):
    """Call visit(dict) for every dict inside node."""
    if isinstance(node, dict):
        visit(node)
        for v in node.values():
            walk(v, visit)
    elif isinstance(node, list):
        for v in node:
            walk(v, visit)


def schema_errors(validator: Draft202012Validator, doc) -> list[str]:
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))]


def vocabulary_problems(model: dict) -> list[str]:
    """Families and members must equal the ADR-010 G8 table exactly."""
    bad = []
    fams = model["vocabulary"]["families"]
    ids = [f["id"] for f in fams]
    if len(ids) != len(set(ids)):
        bad.append("duplicate family id")
    if set(ids) != set(G8_VOCABULARY):
        bad.append(f"families {sorted(set(ids) ^ set(G8_VOCABULARY))} differ from G8")
    for f in fams:
        if "prefix" in f:
            if f["prefix"] not in G8_PREFIXES:
                bad.append(f"family {f['id']} prefix {f['prefix']}")
            bad += [f"{m} outside prefix {f['prefix']}" for m in f["members"] if not m.startswith(f["prefix"])]
        members = f["members"]
        if len(members) != len(set(members)):
            bad.append(f"family {f['id']} duplicate member")
        want = G8_VOCABULARY.get(f["id"], set())
        extra, missing = sorted(set(members) - want), sorted(want - set(members))
        if extra:
            bad.append(f"family {f['id']}: not in G8 {extra}")
        if missing:
            bad.append(f"family {f['id']}: missing G8 {missing}")
    return bad


def guard_problems(model: dict) -> list[str]:
    """Unknown needs:* members must block every consumer action (fail-closed)."""
    bad = []
    der = next((d for d in model["derivations"] if d["name"] == "actionGuard"), None)
    if der is None:
        return ["derivation actionGuard missing"]
    first = der.get("rows", [{}])[0]
    want_when = {"count": {"select": {"family": "hold", "members": "unknown"}, "op": "gt", "value": 0}}
    if first.get("when") != want_when or "fail" not in first.get("result", {}):
        bad.append("first actionGuard row does not fail on unknown needs:* members")
    if model["results"].get("actionGuard") != "actionGuard":
        bad.append("results.actionGuard missing")
    if model["transitions"].get("globalPrecheck") != {"value": {"of": "actionGuard.outcome", "in": ["ok"]}}:
        bad.append("transitions.globalPrecheck does not require actionGuard.outcome ok")
    return bad


def self_test(model: dict, rep: Report) -> None:
    """Negative probes on in-memory copies: the checks above must reject them."""
    m = copy.deepcopy(model)
    next(f for f in m["vocabulary"]["families"] if f["id"] == "gate")["members"].append("gate:invented")
    rep.check(bool(vocabulary_problems(m)), "self-test: vocabulary check rejects an invented member (gate:invented)",
              "not rejected")
    m = copy.deepcopy(model)
    next(f for f in m["vocabulary"]["families"] if f["id"] == "hold")["members"].append("hold:operator")
    rep.check(bool(vocabulary_problems(m)), "self-test: vocabulary check rejects an alias (hold:operator)",
              "not rejected")
    m = copy.deepcopy(model)
    der = next(d for d in m["derivations"] if d["name"] == "actionGuard")
    der["rows"] = der["rows"][1:]
    rep.check(bool(guard_problems(m)), "self-test: guard check rejects a model without the unknown-hold row",
              "not rejected")
    m = copy.deepcopy(model)
    m["transitions"]["globalPrecheck"] = {"always": True}
    rep.check(bool(guard_problems(m)), "self-test: guard check rejects transitions without the guard",
              "not rejected")


def check_model(model: dict, rep: Report) -> None:
    codes = model["outputCodes"]
    fams = {f["id"]: f for f in model["vocabulary"]["families"]}

    # Vocabulary (a): exactly the G8 table, no aliases.
    bad = vocabulary_problems(model)
    rep.check(not bad, "vocabulary: families and members equal the ADR-010 G8 table exactly, no aliases",
              "; ".join(bad))
    bad = guard_problems(model)
    rep.check(not bad, "consumer guard: unknown needs:* members block every transition (fail-closed)",
              "; ".join(bad))

    gate_members = set(fams["gate"]["members"])
    chain_bad = [g for t in ("task", "parent") for g in model["gateChains"][t] if g not in gate_members]
    rep.check(not chain_bad, "gate chains use vocabulary gates only", ", ".join(chain_bad))

    legacy = model["legacyStatuses"]["statuses"]
    rep.check(all(s.startswith("status:") for s in legacy) and len(legacy) == len(set(legacy)),
              "legacy status list (b) well-formed", "bad legacy status")

    meta = model["meta"]
    pre_ok = meta["releaseStatus"] == "released" or ("-" in meta["modelVersion"] and meta["normative"] is False)
    rep.check(pre_ok, "meta: unreleased working state carries a pre-release version and normative=false",
              f"{meta['modelVersion']} / {meta['releaseStatus']} / normative={meta['normative']}")

    # Derivations: names, ordering of references, row ids, codes.
    names: list[str] = []
    problems: list[str] = []
    base = set(model["transitions"]["baseConditions"])
    category = {"type": "type", "terminal": "terminal", "roleExpected": "roleExpected", "roleDrift": "roleDrift",
                "pool": "pool", "minMaturity": "minMaturity"}

    def ref_ok(name: str, known: list[str]) -> bool:
        return name.split(".")[0] in known

    for der in model["derivations"]:
        known = list(names)
        name = der["name"]
        if name in names:
            problems.append(f"derivation {name} defined twice")
        rows = der.get("rows", [])
        ids = [r["id"] for r in rows]
        if len(ids) != len(set(ids)):
            problems.append(f"{name}: duplicate row id")
        if rows and rows[-1]["when"] != {"always": True}:
            problems.append(f"{name}: last row is not a default row")

        def visit(node, known=known, name=name):
            if "of" in node and "in" in node and not ref_ok(node["of"], known):
                problems.append(f"{name}: value.of {node['of']} not derived earlier")
            if "ref" in node and isinstance(node["ref"], str) and not ref_ok(node["ref"], known):
                problems.append(f"{name}: ref {node['ref']} not derived earlier")
            if "sameValue" in node:
                problems.extend(f"{name}: sameValue {x} not derived earlier"
                                for x in node["sameValue"] if x not in known)
            if "family" in node and isinstance(node["family"], str) and node["family"] not in fams:
                problems.append(f"{name}: unknown family {node['family']}")
            if "chainsBy" in node and node["chainsBy"] not in known:
                problems.append(f"{name}: chainsBy {node['chainsBy']} not derived earlier")
            if "propagate" in node and node["propagate"] not in known:
                problems.append(f"{name}: propagate {node['propagate']} not derived earlier")
            if "fail" in node:
                f = node["fail"]
                if f["class"] not in codes["classes"] or f["reason"] not in codes["reasons"].get(f["class"], []) \
                        or f["handoff"] not in codes["handoffs"]:
                    problems.append(f"{name}: fail codes {f} not in output codes (c)")

        walk(der, visit)
        if name in category:
            for r in rows:
                lit = r["result"].get("value", {}).get("literal")
                if lit is not None and lit not in codes[category[name]]:
                    problems.append(f"{name}: literal {lit} not in output codes (c)")
        if name == "modeResult":
            for r in rows:
                lit = r["result"].get("ok", {}).get("mode", {}).get("literal")
                if lit is not None and lit not in codes["mode"]:
                    problems.append(f"modeResult: mode {lit} not in output codes (c)")
        names.append(name)
    for res in model["results"].values():
        if res not in names:
            problems.append(f"result {res} is not a derivation")
    rep.check(not problems, "decision tables: references, row ids, default rows and codes consistent",
              "; ".join(problems))

    # Every reason code is produced by some row.
    produced = set()
    walk(model["derivations"], lambda n: produced.add((n["fail"]["class"], n["fail"]["reason"])) if "fail" in n else None)
    declared = {(c, r) for c, rs in codes["reasons"].items() for r in rs}
    rep.check(produced == declared, "every declared reason code is produced by a table row",
              f"declared-only {sorted(declared - produced)}, undeclared {sorted(produced - declared)}")

    # Transitions.
    cat = {e["id"] for e in model["externalPreconditions"]["catalog"]}
    pw = set(model["postWrite"])
    tproblems = []
    tids = [t["id"] for t in model["transitions"]["items"]]
    if len(tids) != len(set(tids)):
        tproblems.append("duplicate transition id")
    for t in model["transitions"]["items"]:
        tproblems += [f"{t['id']}: unknown external precondition {x}" for x in t["externalPreconditions"] if x not in cat]
        tproblems += [f"{t['id']}: unknown post-write step {x}" for x in t["postWrite"] if x not in pw]
        if not t["externalPreconditions"]:
            tproblems.append(f"{t['id']}: no external precondition named")

        def tvisit(node, t=t):
            if "ref" in node and isinstance(node["ref"], str) and node["ref"] not in base:
                tproblems.append(f"{t['id']}: base condition {node['ref']} unknown")
            if "of" in node and "in" in node and not ref_ok(node["of"], names):
                tproblems.append(f"{t['id']}: value.of {node['of']} unknown")
        walk([t["staticPrecheck"], t.get("exceptions", []), model["transitions"]["globalPrecheck"]], tvisit)
    rep.check(not tproblems, "transitions: ids unique, references resolve, external preconditions named",
              "; ".join(tproblems))
    kinds = {t["kind"] for t in model["transitions"]["items"]}
    need = {"gate-set", "gate-withdraw", "hold-set", "hold-release", "terminal-set", "maturity-change", "exec-change",
            "recovery"}
    rep.check(need <= kinds, "transitions: every transition kind present", f"missing {sorted(need - kinds)}")
    has_exc = {e["id"] for t in model["transitions"]["items"] for e in t.get("exceptions", [])}
    rec = {t["id"] for t in model["transitions"]["items"] if t["kind"] == "recovery"}
    rep.check(any(x.startswith("G7") for x in has_exc) and {"recover-prefix-invalid", "recover-open-terminal"} <= rec,
              "transitions: G7 exception and both recovery paths present", f"exceptions {sorted(has_exc)}, recovery {sorted(rec)}")


def code_problems(fx: dict, codes: dict) -> list[str]:
    out = []
    for stage in ("mode", "contract", "pool", "actionGuard"):
        r = fx["expected"][stage]
        if r["outcome"] == "fail":
            if r["class"] not in codes["classes"]:
                out.append(f"{stage}.class {r['class']}")
            elif r["reason"] not in codes["reasons"][r["class"]]:
                out.append(f"{stage}.reason {r['reason']}")
            if r["handoff"] not in codes["handoffs"]:
                out.append(f"{stage}.handoff {r['handoff']}")
            continue
        fields = {"mode": {"mode": "mode"}, "actionGuard": {"guard": "guard"},
                  "contract": {"type": "type", "top": "top", "maturity": "maturity", "exec": "exec",
                               "terminal": "terminal", "roleExpected": "roleExpected", "roleDrift": "roleDrift"},
                  "pool": {"pool": "pool", "type": "type", "maturity": "maturity", "minMaturity": "minMaturity"}}[stage]
        out += [f"{stage}.{k} {r[k]}" for k, c in fields.items() if r[k] not in codes[c]]
        hold_field = {"contract": "holds", "pool": "hold"}.get(stage)
        if hold_field:
            parts = r[hold_field].split(",")
            if r[hold_field] != "none" and not all(p in codes["holds"] and p != "none" for p in parts):
                out.append(f"{stage}.{hold_field} {r[hold_field]}")
    return out


def check_fixtures(model: dict, fixtures: list[tuple[pathlib.Path, dict]], rep: Report) -> None:
    codes = model["outputCodes"]
    fams = model["vocabulary"]["families"]

    ids = collections.Counter(fx["id"] for _, fx in fixtures)
    dups = sorted(k for k, v in ids.items() if v > 1)
    rep.check(not dups, "fixtures: ids unique", ", ".join(dups))
    stem_bad = [str(p.relative_to(ROOT)) for p, fx in fixtures if p.stem != fx["id"]]
    rep.check(not stem_bad, "fixtures: file name equals id", ", ".join(stem_bad))

    bad = [f"{fx['id']}: {x}" for _, fx in fixtures for x in code_problems(fx, codes)]
    rep.check(not bad, "fixtures: every expected code exists in output codes (c); input labels are not checked",
              "; ".join(bad))

    exp = [fx["expected"] for _, fx in fixtures]
    stages = [r for e in exp for r in e.values()]

    # Coverage: reason codes.
    seen = {(r["class"], r["reason"]) for r in stages if r["outcome"] == "fail"}
    declared = {(c, r) for c, rs in codes["reasons"].items() for r in rs}
    missing = sorted(declared - seen)
    rep.check(not missing, f"coverage: every reason code ({len(declared)})", f"missing {missing}")

    # Coverage: gate stages per type.
    tops = {(e["contract"]["type"], e["contract"]["top"]) for e in exp if e["contract"]["outcome"] == "ok"}
    want = {("task", g.split(":")[1]) for g in model["gateChains"]["task"]} | \
           {("parent", g.split(":")[1]) for g in model["gateChains"]["parent"]}
    rep.check(want <= tops, f"coverage: every gate stage per type ({len(want)})", f"missing {sorted(want - tops)}")

    # Coverage: role projection rows, with consistency of the tag.
    role_rows = next(d for d in model["derivations"] if d["name"] == "roleExpected")["rows"]
    row_result = {r["id"]: r["result"]["value"]["literal"] for r in role_rows}
    tagged = collections.defaultdict(list)
    for _, fx in fixtures:
        row = fx.get("covers", {}).get("roleRow")
        if row:
            tagged[row].append(fx)
    unknown_tags = sorted(set(tagged) - set(row_result))
    missing = sorted(set(row_result) - set(tagged))
    mismatch = [f"{fx['id']}->{row}" for row, lst in tagged.items() if row in row_result for fx in lst
                if fx["expected"]["contract"].get("roleExpected") != row_result[row]]
    rep.check(not missing and not unknown_tags and not mismatch,
              f"coverage: every role projection row ({len(row_result)})",
              f"missing {missing}, unknown tags {unknown_tags}, tag/expectation mismatch {mismatch}")

    # Coverage: holds, terminal states, pools.
    holds = {p for e in exp if e["contract"]["outcome"] == "ok" for p in e["contract"]["holds"].split(",")}
    want = set(codes["holds"]) - {"none"}
    rep.check(want <= holds, "coverage: every hold", f"missing {sorted(want - holds)}")
    terms = {e["contract"]["terminal"] for e in exp if e["contract"]["outcome"] == "ok"}
    rep.check(set(codes["terminal"]) <= terms, "coverage: every terminal state",
              f"missing {sorted(set(codes['terminal']) - terms)}")
    pools = {e["pool"]["pool"] for e in exp if e["pool"]["outcome"] == "ok"}
    rep.check(set(codes["pool"]) <= pools, "coverage: every claim pool", f"missing {sorted(set(codes['pool']) - pools)}")

    # Coverage: duplicates and order independence.
    seq = [fx for _, fx in fixtures if fx["inputKind"] == "evaluator-sequence"]
    seq_ok = [fx["id"] for fx in seq if len(fx["input"]["labels"]) != len(set(fx["input"]["labels"]))]
    rep.check(bool(seq) and len(seq_ok) == len(seq),
              "coverage: duplicate inputs only as inputKind evaluator-sequence",
              f"{len(seq)} evaluator-sequence fixtures, {len(seq_ok)} with duplicates")
    groups = collections.defaultdict(list)
    for _, fx in fixtures:
        if "orderGroup" in fx:
            groups[fx["orderGroup"]].append(fx)
    gprob = []
    for g, lst in groups.items():
        if len(lst) < 2:
            gprob.append(f"{g}: fewer than two fixtures")
        if len({tuple(sorted(fx["input"]["labels"])) + (fx["input"]["state"],) for fx in lst}) != 1:
            gprob.append(f"{g}: label multisets or states differ")
        if len({tuple(fx["input"]["labels"]) for fx in lst}) < 2:
            gprob.append(f"{g}: no differing order")
        if len({json.dumps(fx["expected"], sort_keys=True) for fx in lst}) != 1:
            gprob.append(f"{g}: expectations differ")
    rep.check(bool(groups) and not gprob, "coverage: order independence groups", "; ".join(gprob) or "no group")

    # Coverage: legacy known/unknown/multiple and no mode.
    legacy = collections.defaultdict(list)
    for _, fx in fixtures:
        tag = fx.get("covers", {}).get("legacy")
        if tag:
            legacy[tag].append(fx)
    want_reason = {"unknown": "legacy-status-unknown", "multiple": "legacy-status-multiple"}
    lprob = [t for t in ("known", "unknown", "multiple") if t not in legacy]
    for tag, lst in legacy.items():
        for fx in lst:
            m = fx["expected"]["mode"]
            ok = m.get("mode") == "legacy" if tag == "known" else m.get("reason") == want_reason[tag]
            if not ok:
                lprob.append(f"{fx['id']} tagged {tag}")
    has_none = any(e["mode"].get("mode") == "none" for e in exp)
    rep.check(not lprob and has_none, "coverage: legacy known/unknown/multiple and issues without mode",
              f"problems {lprob}, mode none present={has_none}")

    # Consumer guard: fixtures with an unknown needs:* member expect a blocked guard, and only those.
    hold_members = set(next(f for f in fams if f["id"] == "hold")["members"])
    gprob = []
    for _, fx in fixtures:
        unknown = any(lab.startswith("needs:") and lab not in hold_members for lab in fx["input"]["labels"])
        blocked = fx["expected"]["actionGuard"]["outcome"] == "fail"
        if unknown != blocked:
            gprob.append(f"{fx['id']}: unknown hold={unknown}, guard blocked={blocked}")
    blocked_beside_pool = any(fx["expected"]["actionGuard"]["outcome"] == "fail"
                              and fx["expected"]["pool"]["outcome"] == "ok"
                              and fx["expected"]["pool"]["pool"] != "none" for _, fx in fixtures)
    rep.check(not gprob and blocked_beside_pool,
              "coverage: unknown needs:* blocks the action guard, also beside an open claim pool",
              f"{gprob}, blocked beside open pool={blocked_beside_pool}")

    # Coverage: arbitrary input labels (unknown family members, foreign labels).
    labels = {lab for _, fx in fixtures for lab in fx["input"]["labels"]}
    unknown_by_prefix = {}
    for f in fams:
        if "prefix" in f:
            unknown_by_prefix[f["prefix"]] = [lab for lab in labels if lab.startswith(f["prefix"])
                                              and lab not in f["members"]
                                              and lab not in model["legacyStatuses"]["statuses"]]
    no_unknown = sorted(p for p, lst in unknown_by_prefix.items() if not lst)
    foreign = [lab for lab in labels if not any(lab.startswith(p) for p in G8_PREFIXES) and lab != "epic"]
    rep.check(not no_unknown and bool(foreign), "coverage: unknown members per family and foreign labels in inputs",
              f"no unknown member for {no_unknown}, foreign labels {len(foreign)}")


def main() -> int:
    rep = Report()
    model_schema = load(ROOT / "schema" / "gate-model.schema.json")
    fixture_schema = load(ROOT / "schema" / "fixture.schema.json")
    for name, sch in (("gate-model", model_schema), ("fixture", fixture_schema)):
        try:
            Draft202012Validator.check_schema(sch)
            rep.check(True, f"schema {name}: valid Draft 2020-12")
        except Exception as exc:  # noqa: BLE001
            rep.check(False, f"schema {name}: valid Draft 2020-12", str(exc))

    model = load(ROOT / "model" / "gate-model.json")
    errs = schema_errors(Draft202012Validator(model_schema), model)
    rep.check(not errs, "model: valid against schema/gate-model.schema.json", "; ".join(errs[:10]))

    fx_validator = Draft202012Validator(fixture_schema)
    fixtures = []
    ferrs = []
    for path in sorted((ROOT / "fixtures").rglob("*.json")):
        doc = load(path)
        e = schema_errors(fx_validator, doc)
        ferrs += [f"{path.relative_to(ROOT)}: {x}" for x in e]
        fixtures.append((path, doc))
    rep.check(bool(fixtures) and not ferrs, f"fixtures: {len(fixtures)} files valid against schema/fixture.schema.json",
              "; ".join(ferrs[:10]))

    if not errs:
        check_model(model, rep)
        self_test(model, rep)
        if not ferrs:
            check_fixtures(model, fixtures, rep)

    print()
    print(f"SUMMARY  passed={len(rep.passed)} failed={len(rep.errors)} fixtures={len(fixtures)}")
    print(DISCLAIMER)
    return 0 if not rep.errors else 1


if __name__ == "__main__":
    sys.exit(main())
