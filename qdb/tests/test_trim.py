import pytest

from pyquil import Program
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP

from qdb.utils import trim_program


@pytest.mark.parametrize("qubits", [[0], [1], [2], [0, 1], [0, 2], [1, 2]])
def test_basic(qubits):
    pq = Program(H(0), CNOT(0, 1), CNOT(1, 2))
    trimmed = trim_program(pq, qubits)
    assert trimmed == pq


@pytest.mark.parametrize("qubits", [[0], [1], [2], [0, 1], [0, 2], [1, 2]])
def test_entangled(qubits):
    def construct_program(trimmed):
        pq = Program(H(0), CNOT(0, 1), CNOT(1, 2))
        ro = pq.declare("ro", "BIT", 1)
        pq.measure(0, ro)
        if trimmed:
            pq.if_then(ro, X(0), X(1))
        else:
            pq.if_then(ro, Program(X(0), H(3)), Program(X(1), CZ(3, 4)))
        return pq

    trimmed = trim_program(construct_program(False), qubits)
    assert trimmed == construct_program(True)


@pytest.mark.skip("Not implemented")
def test_if_then():
    def construct_program(trimmed):
        pq = Program(H(0))
        ro = pq.declare("ro", "BIT", 1)
        pq.measure(0, ro)
        if not trimmed:
            pq.if_then(ro, X(1), Y(1))
        return pq

    trimmed = trim_program(construct_program(False), [0])
    assert trimmed == construct_program(True)


@pytest.mark.skip("Not implemented")
def test_simple_control_flow_dependency():
    pq = Program(H(0))
    ro = pq.declare("ro")
    pq.measure(0, ro)
    pq.if_then(ro, X(1))

    trimmed = trim_program(pq, [1])
    assert trimmed == pq


@pytest.mark.skip("Not implemented")
def test_control_flow_dependency():
    def construct_program(trimmed):
        pq = Program(H(0), H(2), CNOT(0, 1), CNOT(2, 3), X(0), X(2))
        ro = pq.declare("ro")
        pq.measure(3, ro)
        if trimmed:
            pq.if_then(ro, X(1))
        else:
            pq.if_then(ro, Program(X(2), X(1)))
        return pq

    trimmed = trim_program(construct_program(False), [1])
    assert trimmed == construct_program(True)


@pytest.mark.skip("Not implemented")
def test_trim_while_loop():
    def construct_program(trimmed):
        pq = Program(H(0))
        if not trimmed:
            pq += Program(H(1))
            ro = pq.declare("ro")
            pq.measure(1, ro)
            pq.while_do(ro, Program(X(1)).measure(1, ro))
        pq += Program(X(0))

    trimmed = trim_program(construct_program(False), [0])
    assert trimmed == construct_program(True)
