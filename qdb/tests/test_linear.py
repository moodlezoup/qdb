from unittest import TestCase

from pyquil import Program
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP
import qdb

# Test programs with no control flow
class TestLinear(TestCase):
    def test_foo(self):
        pq = Program([H(0), CNOT(0, 1), CNOT(1, 2), qdb.Breakpoint([0, 1, 2])])
