from unittest import TestCase
import pytest

import qdb
from pyquil import Program, get_qc
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP
import numpy as np

# Test programs with control flow but no loops
class TestLinear(TestCase):
    @pytest.mark.skip("Not implemented")
    def test_simple(self):
        qc = get_qc("3q", as_qvm=True)

        # TODO: How should we handle this case?
        # |0, 0, 0>  -->  |?, ?, ?>
        pq = Program(H(0))
        ro = pq.declare("ro", "BIT", 1)
        pq.measure(0, ro)
        pq.if_then(ro, X(1), X(2))
        pq += Program(qdb.Breakpoint([0, 1, 2]))

        wf = qdb.debug(qc, pq)
        # TODO: What should the wavefunction look like?
        assert False
