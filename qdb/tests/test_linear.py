from unittest import TestCase
import pytest

import qdb
from pyquil import Program, get_qc
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP
import numpy as np

# Test programs with no control flow
class TestLinear(TestCase):
    @pytest.mark.skip("qdb.debug does not return a Wavefunction")
    def test_simple(self):
        qc = get_qc("3q", as_qvm=True)

        # |0, 0, 0>  -->  |+, 0, 1>
        pq = Program([H(0), X(1), SWAP(1, 2)])
        true_amplitudes = np.array([0, 1, 0, 0, 0, 1, 0, 0]) / np.sqrt(2)

        wf = qdb.Qdb(qc, pq).do_tomography()

        amplitudes = np.array([wf[i] for i in range(2 ** len(wf))])
        assert np.allclose(true_amplitudes, amplitudes)
