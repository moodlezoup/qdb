from unittest import TestCase
import pytest

from pyquil import Program, get_qc
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP
import qdb


class TestTrim(TestCase):
    def test_basic(self):
        qc = get_qc("3q-qvm")
        pq = Program([H(0), CNOT(0, 1), CNOT(1, 2)])
        trimmed = qdb.Qdb(qc, pq).trim_program([0, 1, 2])
        self.assertEqual(trimmed, pq)

    def test_entangled(self):
        def construct_program(trimmed):
            pq = Program([H(0), CNOT(0, 1), CNOT(1, 2)])
            pq.declare("ro", "BIT", 1)
            pq.measure(0, "ro")
            if trimmed:
                pq.if_then("ro", X(0), X(1))
            else:
                pq.if_then("ro", Program([X(0), H(3)]), Program([X(1), CZ(3, 4)]))
            return pq

        qc = get_qc("3q-qvm")
        trimmed = qdb.Qdb(qc, construct_program(False)).trim_program([0, 1, 2])
        self.assertEqual(trimmed, construct_program(True))

    @pytest.mark.skip("Not implemented")
    def test_if_then(self):
        def construct_program(trimmed):
            pq = Program(H(0))
            pq.declare("ro", "BIT", 1)
            pq.measure(0, "ro")
            if not trimmed:
                pq.if_then("ro", X(1), Y(1))
            return pq

        qc = get_qc("3q-qvm")
        trimmed = qdb.Qdb(qc, construct_program(False)).trim_program([0])
        self.assertEqual(trimmed, construct_program(True))
