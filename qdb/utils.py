from typing import List, Set
import networkx as nx
from qdb.control_flow_graph import QuilControlFlowGraph
from pyquil import Program
from pyquil.quilbase import Gate


def get_necessary_qubits(
    cfg: QuilControlFlowGraph, block_idx: int, qubits: List[int]
) -> Set[int]:
    """
    Returns the set of qubits that are necessary to run tomography on `qubits` at the
    basic block `block` for any execution path in `cfg`.
    """
    if len(qubits) == 0:
        return set()

    # FIXME: Does not pass `test_simple_control_flow`

    # The set of qubits or classical bits that any later control flow depends on
    dependency_graph = cfg.blocks[block_idx].get_local_dependency_graph()
    for i in nx.descendants(cfg, block_idx):
        dependency_graph.add_edges_from(
            cfg.blocks[i].get_local_dependency_graph().edges
        )
    bits = list(cfg.blocks[block_idx].get_control_flow_bits())
    if len(dependency_graph.edges) == 0 or len(bits) == 0:
        control_flow_dependencies = set()
    else:
        control_flow_dependencies = set(
            [i for i in nx.dfs_tree(dependency_graph, bits[0]) if isinstance(i, int)]
        )

    # Build the complete graph of dependent qubits with respect to this block
    entangled_graph = cfg.blocks[block_idx].get_local_entangled_graph()
    for i in nx.ancestors(cfg, block_idx) | nx.descendants(cfg, block_idx):
        entangled_graph.add_edges_from(cfg.blocks[i].get_local_entangled_graph().edges)
    nx.add_path(entangled_graph, control_flow_dependencies)
    nx.add_path(entangled_graph, qubits)

    if len(entangled_graph.edges) == 0:
        return set(qubits) | control_flow_dependencies

    return set(nx.dfs_tree(entangled_graph, qubits[0])) | control_flow_dependencies


def trim_program(pq: Program, qubits: List[int]) -> Program:
    """
    Return a program with only the necessary instructions to compute tomography with
    `qubits`
    """
    cfg = QuilControlFlowGraph(pq)
    unused_instructions = []
    for block_idx, block in enumerate(cfg.blocks):
        necessary_qubits = get_necessary_qubits(cfg, block_idx, qubits)
        for i, inst in enumerate(block.body):
            if isinstance(inst, Gate):
                gate_qubits = set(inst.get_qubits())
                if not necessary_qubits & gate_qubits:
                    unused_instructions.append(block.start_index + i)

    trimmed_program = Program(
        [inst for i, inst in enumerate(pq) if i not in unused_instructions]
    )
    # TODO: Try to remove unused basic blocks and repeat until convergence
    return trimmed_program
