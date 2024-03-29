import pytest
import numpy as np

from pyquil import Program, get_qc
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP

import qdb


# Test programs with no control flow
@pytest.mark.skip("do_tomography returns full density matrix for now")
def test_simple():
    qc = get_qc("3q-qvm")

    # |0, 0, 0>  -->  |+, 0, 1>
    pq = Program(H(0), X(1), SWAP(1, 2))
    true_amplitudes = np.array([0, 1, 0, 0, 0, 1, 0, 0]) / np.sqrt(2)

    rho_est = qdb.Qdb(qc, pq).do_tomography("0 1 2")

    amplitudes = np.array([wf[i] for i in range(2 ** len(wf))])
    assert np.allclose(true_amplitudes, amplitudes)
