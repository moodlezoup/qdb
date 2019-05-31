import typing
from typing import List, Set

from pyquil import Program
from pyquil.quilbase import Gate

from qdb.control_flow_graph import QuilControlFlowGraph


def entanglement_set(pq: Program, qubits: List[int]) -> Set[int]:
    """
    Returns a conservative overestimate of the set of qubits entangled with
    one or more of those provided, based entirely on which multi-qubit gates
    have been performed so far.
    """
    # FIXME: This only works within a single basic block since unrelated qubits
    #        can affect control flow.
    # TODO: It is probably better to first build a graph and use
    #       `networkx.descendants` or something similar
    entangled_qubits = set(qubits)
    num_entangled_prev = 0
    while len(entangled_qubits) != num_entangled_prev:
        num_entangled_prev = len(entangled_qubits)
        for gate in pq:
            if isinstance(gate, Gate):
                gate_qubits = set(gate.get_qubits())
                if entangled_qubits & gate_qubits:
                    entangled_qubits |= gate_qubits
    return entangled_qubits

def trim_program(pq: Program, qubits: List[int]) -> Program:
    entangled_qubits = entanglement_set(pq, qubits)
    trimmed_program = Program()
    for inst in pq:
        if isinstance(inst, Gate):
            gate_qubits = set(inst.get_qubits())
            if entangled_qubits & gate_qubits:
                trimmed_program += inst
        else:
            trimmed_program += inst
    # FIXME: Once some instructions are trimmed, it is possible that the control
    #        flow graph can be pruned which could affect the entangled set. This
    #        should be ok in the common case, though.
    if not QuilControlFlowGraph(trimmed_program).is_dag():
        raise ValueError("Program is not a dag.")
    return trimmed_program
