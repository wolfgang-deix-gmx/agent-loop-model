"""Negative tests for the test-only interpreter."""
import copy
import json
from pathlib import Path
import unittest

from interpreter import Interpreter, ModelError

ROOT = Path(__file__).resolve().parents[2]
MODEL = json.loads((ROOT / 'model/gate-model.json').read_text(encoding='utf-8'))


class FailClosed(unittest.TestCase):
    def machine(self):
        return Interpreter(copy.deepcopy(MODEL), 'OPEN', [])

    def test_unknown_condition(self):
        with self.assertRaises(ModelError): self.machine().condition({'future': True})

    def test_unknown_expression(self):
        with self.assertRaises(ModelError): self.machine().expression({'future': 'x'})

    def test_unknown_selector(self):
        with self.assertRaises(ModelError): self.machine().select({'future': 'x'})

    def test_reference_not_derived(self):
        with self.assertRaises(ModelError): self.machine().lookup('future.outcome', missing_ok=True)

    def test_no_matching_row(self):
        machine = self.machine()
        machine.model['derivations'][0]['rows'] = [{
            'when': {'has': 'absent'}, 'result': {'value': {'literal': 'x'}}}]
        with self.assertRaises(ModelError): machine.derive()

    def test_unknown_transition(self):
        machine = self.machine()
        machine.derive()
        with self.assertRaises(ModelError): machine.transition('unknown-transition')


if __name__ == '__main__':
    unittest.main()
