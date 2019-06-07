import pytest

from pyquil import Program
from pyquil.gates import X, H, CNOT, RESET
from pyquil.quilbase import JumpTarget, Jump
from pyquil.quilatom import Label

from qdb import QuilControlFlowGraph
from qdb.utils import force_execution_path


def test_linear():
    pq = Program(H(0), CNOT(0, 1), CNOT(1, 2))
    # Ignore the start label
    assert pq == force_execution_path(pq, QuilControlFlowGraph(pq), [0])[1:]


def test_simple():
    def construct_program(path=None):
        if path is None:
            pq = Program(H(0))
        else:
            label_start = Label("START-BRANCH-REWIRE")
            pq = Program(JumpTarget(label_start), H(0))

        ro = pq.declare("ro")
        pq.measure(0, ro)
        if path is None:
            pq.if_then(ro, X(1), X(2))
        elif path == [0, 1, 3]:
            pq.if_then(ro, Program(RESET(), Jump(label_start)), X(2))
        elif path == [0, 2, 3]:
            pq.if_then(ro, X(1), Program(RESET(), Jump(label_start)))
        return pq

    pq = construct_program()
    pq_taken = construct_program([0, 1, 3])
    pq_not_taken = construct_program([0, 2, 3])
    cfg = QuilControlFlowGraph(pq)

    assert pq_taken == force_execution_path(pq, cfg, [0, 1, 3])
    assert pq_not_taken == force_execution_path(pq, cfg, [0, 2, 3])
