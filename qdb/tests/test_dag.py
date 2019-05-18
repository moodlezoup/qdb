from unittest import TestCase

from pyquil import Program
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP
import qdb

# Test programs with control flow but no loops
class TestDAG(TestCase):
    def test_foo(self):
        pq = Program([H(0), CNOT(0, 1), CNOT(1, 2)])
        ro = pq.declare("ro", "BIT", 1)
        pq.measure(0, ro)
        pq.if_then(ro, X(0), X(1))
