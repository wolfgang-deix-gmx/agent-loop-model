#!/usr/bin/env python3
"""Test-only conformance runner; not normative or a consumer runtime."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from interpreter import Interpreter, ModelError

ROOT = Path(__file__).resolve().parents[2]
FIELDS = {'roleExpected': 'role_expected', 'roleActual': 'role_actual',
          'roleDrift': 'role_drift', 'minMaturity': 'min_maturity'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def serialize(result):
    return ' '.join([result['outcome']] + [f'{FIELDS.get(k, k)}={v}'
                    for k, v in result.items() if k != 'outcome'])


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluator', required=True, type=Path)
    parser.add_argument('--label-manifest', required=True, type=Path)
    args = parser.parse_args()
    model = read(ROOT / 'model/gate-model.json')
    manifest = read(args.label_manifest)
    git_bash = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/bin/bash.exe'
    bash = str(git_bash) if os.name == 'nt' and git_bash.is_file() else shutil.which('bash')
    if not bash: raise ModelError('native Git Bash not found')
    env = os.environ.copy()
    env.pop('LOOP_E4_CUTOVER', None)
    env.pop('LOOP_E4_CUTOVER_FLAG', None)
    errors, coverage = [], {}
    classification = sorted(p for p in (ROOT / 'fixtures').rglob('*.json') if 'transitions' not in p.parts)
    for path in classification:
        fx = read(path)
        machine = Interpreter(model, **fx['input'])
        results = machine.derive()
        if results != fx['expected']:
            errors.append(f"{fx['id']}: model {results!r} != expected {fx['expected']!r}")
        script = 'p="$1"; shift; if command -v cygpath >/dev/null; then p="$(cygpath -u "$p")"; fi; . "$p" || exit 2; "$@"'
        for result, function in [('mode', 'gate_mode_classify'), ('contract', 'gate_contract_check'), ('pool', 'gate_claim_pool')]:
            command = [bash, '-c', script, 'conformance', str(args.evaluator.resolve()), function,
                       fx['input']['state'], *fx['input']['labels']]
            completed = subprocess.run(command, env=env, capture_output=True, text=True)
            expected = serialize(fx['expected'][result])
            rc = 0 if fx['expected'][result]['outcome'] == 'ok' else 1
            if completed.returncode != rc or completed.stdout.strip() != expected:
                errors.append(f"{fx['id']}: {function} exit={completed.returncode}, output={completed.stdout.strip()!r}, expected exit={rc} {expected!r}; stderr={completed.stderr.strip()!r}")
        for kind, values in machine.coverage.items(): coverage.setdefault(kind, set()).update(values)
    transition_paths = sorted((ROOT / 'fixtures/transitions').rglob('*.json'))
    for path in transition_paths:
        fx = read(path)
        machine = Interpreter(model, **fx['input'])
        machine.derive()
        actual = machine.transition(fx['transition'])
        expected = {'admissible': fx['admissible'], 'path': fx['path']}
        if actual != expected: errors.append(f"{fx['id']}: transition {actual!r} != {expected!r}")
        for kind, values in machine.coverage.items(): coverage.setdefault(kind, set()).update(values)
    vocabulary = {label for family in model['vocabulary']['families'] for label in family['members']}
    labels = {item['name'] for item in manifest['labels']}
    existing = {'needs:operator', 'role:architect', 'role:operator', 'role:coder', 'role:reviewer',
                'status:finished', 'status:abandoned', 'epic'}
    if labels - vocabulary or vocabulary - labels != existing:
        errors.append(f'label manifest mismatch: missing={labels-vocabulary}; remainder={vocabulary-labels}')
    for kind in ['has', 'count', 'duplicates', 'state', 'value', 'sameValue', 'ref', 'all', 'any', 'not']:
        if coverage.get(kind, set()) != {True, False}: errors.append(f'condition coverage {kind}: {coverage.get(kind, set())}')
    if True not in coverage.get('always', set()): errors.append('condition coverage always missing')
    if not transition_paths: errors.append('no transition fixtures')
    print(f'D1: {len(classification)} classifications; D1t: {len(transition_paths)} transitions; D2: {len(classification)*3} evaluator results; D5: {len(labels)} labels')
    print('actionGuard has no evaluator counterpart; D3, D4 and D6 require review.')
    for error in errors: print('FAIL:', error)
    print(f'SUMMARY: {len(errors)} discrepancies')
    return 1 if errors else 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except (ModelError, OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(2)
