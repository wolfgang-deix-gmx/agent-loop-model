"""Test-only interpreter; not normative and not a consumer runtime."""

from collections import Counter, defaultdict
import operator


class ModelError(ValueError):
    """The model uses an unsupported or unresolved expression."""


class Interpreter:
    def __init__(self, model, state, labels):
        self.model, self.state, self.labels = model, state, labels
        self.values = {}
        self.coverage = defaultdict(set)
        self.families = {f['id']: f for f in model['vocabulary']['families']}

    def select(self, selector):
        if 'family' in selector:
            f = self.families[selector['family']]
            def match(label):
                belongs = label.startswith(f['prefix']) if 'prefix' in f else label == f['exact']
                known = label in f['members']
                return belongs and (selector['members'] == 'all' or
                                    (selector['members'] == 'known' and known) or
                                    (selector['members'] == 'unknown' and not known))
            return [label for label in self.labels if match(label)]
        if 'labels' in selector:
            return [label for label in self.labels if label in selector['labels']]
        if 'set' in selector and selector['set'] == 'legacyStatuses':
            return [label for label in self.labels if label in self.model['legacyStatuses']['statuses']]
        if 'anyOf' in selector:
            # Membership per occurrence, not concatenation of overlapping selectors.
            selected = set().union(*(set(self.select(s)) for s in selector['anyOf']))
            return [label for label in self.labels if label in selected]
        raise ModelError(f'unknown selector: {selector}')

    def lookup(self, path, missing_ok=False):
        parts = path.split('.')
        if parts[0] not in self.values:
            raise ModelError(f'not previously derived: {path}')
        value = self.values[parts[0]]
        for part in parts[1:]:
            if not isinstance(value, dict) or part not in value:
                if missing_ok:
                    return None
                raise ModelError(f'missing value: {path}')
            value = value[part]
        return value

    def expression(self, expr):
        if len(expr) != 1:
            raise ModelError(f'invalid expression: {expr}')
        kind, arg = next(iter(expr.items()))
        if kind == 'literal':
            return arg
        if kind == 'ref':
            return self.lookup(arg)
        if kind == 'suffix':
            labels = self.select({'family': arg['family'], 'members': 'all'})
            prefix = self.families[arg['family']]['prefix']
            return labels[0][len(prefix):] if len(labels) == 1 else arg['empty']
        if kind == 'highestPresent':
            chain = self.model['gateChains'][self.lookup(arg['chainsBy'])]
            found = [label.split(':', 1)[1] for label in chain if label in self.labels]
            return found[-1] if found else arg['empty']
        if kind == 'joinPresent':
            found = [label for label in arg['labels'] if label in self.labels]
            return arg['separator'].join(found) if found else arg['empty']
        if kind == 'joinSuffixes':
            found = sorted(label.split(':', 1)[-1] for label in self.select(arg['select']))
            return arg['separator'].join(found) if found else arg['empty']
        raise ModelError(f'unknown expression: {kind}')

    def condition(self, condition):
        if len(condition) != 1:
            raise ModelError(f'invalid condition: {condition}')
        kind, arg = next(iter(condition.items()))
        if kind == 'has': result = arg in self.labels
        elif kind == 'count':
            ops = {'eq': operator.eq, 'ne': operator.ne, 'lt': operator.lt,
                   'le': operator.le, 'gt': operator.gt, 'ge': operator.ge}
            if arg['op'] not in ops: raise ModelError(f"unknown operator: {arg['op']}")
            result = ops[arg['op']](len(self.select(arg['select'])), arg['value'])
        elif kind == 'duplicates': result = any(n > 1 for n in Counter(self.select(arg['select'])).values())
        elif kind == 'state': result = self.state in arg['in']
        elif kind == 'value': result = self.lookup(arg['of'], missing_ok=True) in arg['in']
        elif kind == 'sameValue': result = self.lookup(arg[0], missing_ok=True) == self.lookup(arg[1], missing_ok=True)
        elif kind == 'ref':
            if arg not in self.model['transitions']['baseConditions']: raise ModelError(f'unknown condition ref: {arg}')
            result = self.condition(self.model['transitions']['baseConditions'][arg])
        elif kind == 'always': result = arg is True
        elif kind == 'all': result = all([self.condition(item) for item in arg])
        elif kind == 'any': result = any([self.condition(item) for item in arg])
        elif kind == 'not': result = not self.condition(arg)
        else: raise ModelError(f'unknown condition: {kind}')
        self.coverage[kind].add(result)
        return result

    def derive(self):
        for derivation in self.model['derivations']:
            if 'expr' in derivation:
                result = self.expression(derivation['expr'])
            else:
                row = next((row for row in derivation['rows'] if self.condition(row['when'])), None)
                if row is None: raise ModelError(f"no matching row: {derivation['name']}")
                result_spec = row['result']
                if 'value' in result_spec: result = self.expression(result_spec['value'])
                elif 'ok' in result_spec: result = {'outcome': 'ok', **{k: self.expression(v) for k, v in result_spec['ok'].items()}}
                elif 'fail' in result_spec: result = {'outcome': 'fail', **result_spec['fail']}
                elif 'propagate' in result_spec: result = self.lookup(result_spec['propagate'])
                else: raise ModelError(f'unknown row result: {result_spec}')
            self.values[derivation['name']] = result
        return {k: self.lookup(v) for k, v in self.model['results'].items()}

    def transition(self, transition_id):
        item = next((t for t in self.model['transitions']['items'] if t['id'] == transition_id), None)
        if item is None: raise ModelError(f'unknown transition: {transition_id}')
        guard = self.condition(self.model['transitions']['globalPrecheck'])
        regular = self.condition(item['staticPrecheck'])
        exceptions = [e['id'] for e in item.get('exceptions', []) if self.condition(e['staticPrecheck'])]
        candidate = regular or bool(exceptions)
        if not guard and candidate: return {'admissible': False, 'path': 'guard'}
        if not guard or not candidate: return {'admissible': False, 'path': 'none'}
        if regular: return {'admissible': True, 'path': 'regular'}
        if len(exceptions) != 1: raise ModelError('ambiguous matching exceptions')
        return {'admissible': True, 'path': 'exception:' + exceptions[0]}
