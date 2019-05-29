import pytest

from pyquil import Program, get_qc
from pyquil.gates import X, Y, Z, H, CZ, CNOT, SWAP
import qdb


@pytest.mark.parametrize("qubits", [[0], [1], [2], [0, 1], [0, 2], [1, 2]])
def test_basic(qubits):
    qc = get_qc("3q-qvm")
    pq = Program([H(0), CNOT(0, 1), CNOT(1, 2)])
    trimmed = qdb.Qdb(qc, pq).trim_program(qubits)
    assert trimmed == pq


def test_entangled():
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
    assert trimmed == construct_program(True)


@pytest.mark.skip("Not implemented")
def test_if_then():
    def construct_program(trimmed):
        pq = Program(H(0))
        pq.declare("ro", "BIT", 1)
        pq.measure(0, "ro")
        if not trimmed:
            pq.if_then("ro", X(1), Y(1))
        return pq

    qc = get_qc("3q-qvm")
    trimmed = qdb.Qdb(qc, construct_program(False)).trim_program([0])
    assert trimmed == construct_program(True)


@pytest.mark.skip("Not implemented")
def test_simple_control_flow_dependency():
    pq = Program(H(0))
    ro = pq.declare("ro")
    pq.measure(0, ro)
    pq.if_then(ro, X(1))

    qc = get_qc("2q-qvm")
    trimmed = qdb.Qdb(qc, pq).trim_program([1])
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

    qc = get_qc("4q-qvm")
    trimmed = qdb.Qdb(qc, construct_program(False)).trim_program([1])
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

    qc = get_qc("2q-qvm")
    trimmed = qdb.Qdb(qc, construct_program(False)).trim_program([0])
    assert trimmed == construct_program(True)
