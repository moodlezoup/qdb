import pytest

from qdb.control_flow_graph import QuilControlFlowGraph
from pyquil import Program
from pyquil.gates import CNOT, CCNOT


@pytest.mark.parametrize(
    "pq",
    [
        Program(CCNOT(0, 1, 2)),
        Program(CNOT(0, 1), CNOT(1, 2)),
        Program(CNOT(0, 1), CNOT(0, 2)),
    ],
)
def test_simple(pq):
    G = QuilControlFlowGraph(pq)
    assert len(G.blocks) == 1
    for qubits in ([0], [1], [2]):
        assert G.blocks[0].get_local_entangled_qubits(qubits) == set([0, 1, 2])


@pytest.mark.parametrize(
    "pq",
    [
        Program(CCNOT(0, 1, 2), CNOT(3, 4)),
        Program(CNOT(0, 1), CNOT(1, 2), CNOT(3, 4)),
        Program(CNOT(0, 1), CNOT(0, 2), CNOT(3, 4)),
    ],
)
def test_disjoint(pq):
    G = QuilControlFlowGraph(pq)
    assert len(G.blocks) == 1
    for qubits in ([0], [1], [2]):
        assert G.blocks[0].get_local_entangled_qubits(qubits) == set([0, 1, 2])
    for qubits in ([3], [4]):
        assert G.blocks[0].get_local_entangled_qubits(qubits) == set([3, 4])


def test_simple_control_flow():
    pq = Program(CNOT(0, 1), CNOT(2, 3))
    ro = pq.declare("ro")
    ro2 = pq.declare("ro2")
    pq.measure(0, ro)
    pq.measure(2, ro2)
    pq.if_then(ro, Program())
    pq.if_then(ro2, Program())

    G = QuilControlFlowGraph(pq)
    assert len(G.blocks) == 1
    assert G.blocks[0].get_local_control_flow_dependent_qubits() == set([0, 1, 2, 3])
