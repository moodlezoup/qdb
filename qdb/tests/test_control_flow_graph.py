from unittest import TestCase
import pytest

from qdb.control_flow_graph import get_control_flow_graph, is_dag
import networkx as nx
from pyquil import Program
from pyquil.gates import X, H, CNOT, CCNOT, RX, NEG, AND, ADD, EQ
from pyquil.gates import EXCHANGE, CONVERT, LOAD, STORE, HALT, WAIT


class TestControlFlowGraph(TestCase):
    def test_simple(self):
        pq = Program(H(0), CNOT(0, 1))

        G, basic_blocks = get_control_flow_graph(pq)

        assert len(basic_blocks) == 1
        assert set(G.nodes) == set(["root", 0])
        assert set(G.edges) == set([("root", 0)])
        assert is_dag(pq)

    def test_if(self):
        pq = Program(H(0), CNOT(0, 1))
        ro = pq.declare("ro")
        pq.measure(0, ro)
        pq.if_then(ro, X(0), X(1))

        G, basic_blocks = get_control_flow_graph(pq)

        assert len(basic_blocks) == 4
        assert set(G.nodes) == set(["root"] + list(range(len(basic_blocks))))
        assert set(G.edges) == set([("root", 0), (0, 1), (0, 2), (1, 3), (2, 3)])
        assert is_dag(pq)

    def test_while(self):
        pq = Program(H(0), CNOT(0, 1))
        ro = pq.declare("ro")
        pq.measure(0, ro)
        q_program = Program(X(1))
        q_program.measure(0, ro)
        pq.while_do(ro, q_program)

        G, basic_blocks = get_control_flow_graph(pq)

        assert len(basic_blocks) == 4
        assert set(G.nodes) == set(["root"] + list(range(len(basic_blocks))))
        assert set(G.edges) == set([("root", 0), (0, 1), (1, 2), (1, 3), (2, 1)])
        assert not is_dag(pq)

    def test_all_instructions(self):
        pq = Program(H(0), X(1), RX(1.2, 2), CNOT(0, 1), CCNOT(0, 1, 2))
        ro = pq.declare("ro")
        pq.measure(0, ro)
        pq.defgate("mygate", [[1, 0], [0, 1]])
        pq.inst(("mygate", 0))
        pq.reset(0)
        pq += Program(NEG(ro), AND(ro, ro), ADD(ro, 1), EQ(ro, ro, ro))
        pq += Program(EXCHANGE(ro, ro), CONVERT(ro, ro))
        pq += Program(LOAD(ro, ro, ro), STORE(ro, ro, ro))

        G, basic_blocks = get_control_flow_graph(pq)

        assert len(basic_blocks) == 1
        assert set(G.nodes) == set(["root", 0])
        assert set(G.edges) == set([("root", 0)])
        assert is_dag(pq)

    def test_halt(self):
        # TODO: How should we handle `WAIT`?
        pq = Program(H(0))
        ro = pq.declare("ro", 0)
        pq.measure(0, ro)
        pq.if_then(ro, HALT)
        pq += Program(X(0))

        G, basic_blocks = get_control_flow_graph(pq)

        assert len(basic_blocks) == 4
        assert set(G.nodes) == set(["root"] + list(range(len(basic_blocks))))
        assert set(G.edges) == set([("root", 0), (0, 1), (0, 2), (1, 3)])
        assert is_dag(pq)
