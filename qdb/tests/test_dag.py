import pytest

import qdb
from pyquil import Program, get_qc
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP
import numpy as np

# Test programs with control flow but no loops
@pytest.mark.skip("Not implemented")
def test_simple():
    qc = get_qc("3q-qvm")

    # |0, 0, 0>  -->  |0, 1, 0> or |1, 0, 1> (a mixed state)
    pq = Program(H(0))
    ro = pq.declare("ro", "BIT", 1)
    pq.measure(0, ro)
    pq.if_then(ro, X(1), X(2))

    wf = qdb.Qdb(qc, pq).do_tomography("0 1 2")
    # TODO: What should the wavefunction look like?
    assert False
