import qdb
from pyquil import Program, get_qc, list_quantum_computers
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP
import numpy as np
from pyquil.api import QVMConnection

pq = Program()
qc = get_qc("3q-qvm")
qdb.set_trace(pq, qc)
pq += H(0)
pq += X(1)
pq += SWAP(1, 2)
