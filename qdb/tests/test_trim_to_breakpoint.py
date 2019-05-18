from unittest import TestCase
import pytest

from pyquil import Program
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP
from qdb import Breakpoint, trim_to_breakpoint


class TestTrim(TestCase):
    def test_basic(self):
        pq = Program([H(0), CNOT(0, 1), CNOT(1, 2), Breakpoint([0, 1, 2])])
        self.assertEqual(trim_to_breakpoint(pq), pq)

    def test_entangled(self):
        def construct_program(trimmed):
            pq = Program([H(0), CNOT(0, 1), CNOT(1, 2)])
            pq.declare("ro", "BIT", 1)
            pq.measure(0, "ro")
            if trimmed:
                pq.if_then("ro", X(0), X(1))
            else:
                pq.if_then("ro", Program([X(0), H(3)]), Program([X(1), CZ(3, 4)]))
            pq += Breakpoint([0, 1, 2])
            return pq

        self.assertEqual(
            trim_to_breakpoint(construct_program(False)), construct_program(True)
        )

    @pytest.mark.skip("Not implemented")
    def test_if_then(self):
        def construct_program(trimmed):
            pq = Program(H(0))
            pq.declare("ro", "BIT", 1)
            pq.measure(0, "ro")
            if not trimmed:
                pq.if_then("ro", X(1), Y(1))
            pq += Breakpoint([0])
            return pq

        self.assertEqual(
            trim_to_breakpoint(construct_program(False)), construct_program(True)
        )
