import pytest

from qdb.control_flow_graph import QuilControlFlowGraph
import networkx as nx
from pyquil import Program
from pyquil.gates import X, H, CNOT, CCNOT, RX, NEG, AND, ADD, EQ
from pyquil.gates import EXCHANGE, CONVERT, LOAD, STORE, HALT, WAIT


def test_simple():
    pq = Program(H(0), CNOT(0, 1))

    G = QuilControlFlowGraph(pq)

    assert len(G.blocks) == 1
    assert set(G.nodes) == set([0])
    assert set(G.edges) == set()
    assert G.is_dag()


def test_if():
    pq = Program(H(0), CNOT(0, 1))
    ro = pq.declare("ro")
    pq.measure(0, ro)
    pq.if_then(ro, X(0), X(1))

    G = QuilControlFlowGraph(pq)

    assert len(G.blocks) == 3
    assert set(G.nodes) == set(list(range(len(G.blocks))))
    assert set(G.edges) == set([(0, 1), (0, 2)])
    assert G.is_dag()


@pytest.mark.skip("Not implemented")
def test_while():
    pq = Program(H(0), CNOT(0, 1))
    ro = pq.declare("ro")
    pq.measure(0, ro)
    q_program = Program(X(1))
    q_program.measure(0, ro)
    pq.while_do(ro, q_program)

    G = QuilControlFlowGraph(pq)

    assert len(G.blocks) == 4
    assert set(G.nodes) == set(list(range(len(G.blocks))))
    assert set(G.edges) == set([(0, 1), (1, 2), (1, 3), (2, 1)])
    assert not G.is_dag()


def test_all_instructions():
    pq = Program(H(0), X(1), RX(1.2, 2), CNOT(0, 1), CCNOT(0, 1, 2))
    ro = pq.declare("ro")
    pq.measure(0, ro)
    pq.defgate("mygate", [[1, 0], [0, 1]])
    pq.inst(("mygate", 0))
    pq.reset(0)
    pq += Program(NEG(ro), AND(ro, ro), ADD(ro, 1), EQ(ro, ro, ro))
    pq += Program(EXCHANGE(ro, ro), CONVERT(ro, ro))
    pq += Program(LOAD(ro, ro, ro), STORE(ro, ro, ro))

    G = QuilControlFlowGraph(pq)

    assert len(G.blocks) == 1
    assert set(G.nodes) == set([0])
    assert set(G.edges) == set()
    assert G.is_dag()


def test_halt():
    # TODO: How should we handle `WAIT`?
    pq = Program(H(0))
    ro = pq.declare("ro", 0)
    pq.measure(0, ro)
    pq.if_then(ro, HALT)
    pq += Program(X(0))

    G = QuilControlFlowGraph(pq)

    assert len(G.blocks) == 2
    assert set(G.nodes) == set(list(range(len(G.blocks))))
    assert set(G.edges) == set([(0, 1)])
    assert G.is_dag()
