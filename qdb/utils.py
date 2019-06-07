from typing import List, Set
import networkx as nx
import itertools
from pyquil import Program
from pyquil.quilbase import Gate, JumpTarget, Jump
from pyquil.quilatom import Label

from qdb.control_flow_graph import QuilControlFlowGraph


def get_necessary_qubits(
    cfg: QuilControlFlowGraph, block_idx: int, qubits: List[int]
) -> Set[int]:
    """
    Returns the set of qubits that are necessary to run tomography on `qubits` at the
    basic block `block` for any execution path in `cfg`.
    """
    if len(qubits) == 0:
        return set()

    # The set of qubits or classical bits that determine later control flow
    control_flow_dependencies = set(
        itertools.chain.from_iterable(
            [
                cfg.blocks[i].get_local_control_flow_qubits()
                for i in nx.descendants(cfg, block_idx) | set([block_idx])
            ]
        )
    )
    # The dependency graph of qubits or classical bits that dermine later control flow
    dependency_graph = cfg.blocks[block_idx].get_local_dependency_graph()
    for i in nx.descendants(cfg, block_idx):
        dependency_graph.add_edges_from(
            cfg.blocks[i].get_local_dependency_graph().edges
        )

    # Build the complete graph of dependent qubits with respect to this block
    entangled_graph = cfg.blocks[block_idx].get_local_entangled_graph()
    for i in nx.ancestors(cfg, block_idx) | nx.descendants(cfg, block_idx):
        entangled_graph.add_edges_from(cfg.blocks[i].get_local_entangled_graph().edges)
    entangled_graph.add_edges_from(dependency_graph.edges)
    nx.add_path(entangled_graph, set(qubits) | control_flow_dependencies)

    def filter_qubits(nodes):
        return set(filter(lambda i: isinstance(i, int), nodes))

    if len(entangled_graph.edges) == 0:
        return set(qubits) | filter_qubits(control_flow_dependencies)

    return filter_qubits(nx.dfs_tree(entangled_graph, qubits[0]))


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


def force_execution_path(
    pq: Program, cfg: QuilControlFlowGraph, path: List[int]
) -> Program:
    """
    Force a program to take an execution path by replacing other blocks with the
    instructions `RESET` and `JUMP @START`
    """
    assert nx.is_simple_path(cfg, path), f"{path} is not a simple path"
    assert path[0] == 0, f"{path} does not start at zero"
    assert path[-1] == len(cfg.blocks) - 1, f"{path} does not end at breakpoint"

    unused_block_length = dict(
        [
            (b.start_index, len(b.body))
            for i, b in enumerate(cfg.blocks)
            if i not in path
        ]
    )
    # FIXME: Can't use LabelPlaceholder because that messes up label numbers for testing
    label_start = Label("START-BRANCH-REWIRE")
    rewired_pq = Program(JumpTarget(label_start))
    i = 0
    while i < len(pq):
        inst = pq[i]
        if i in unused_block_length:
            if isinstance(inst, JumpTarget):
                rewired_pq += inst
            rewired_pq.reset()
            rewired_pq += Jump(label_start)
            i += unused_block_length[i]
        else:
            rewired_pq += inst
            i += 1

    return rewired_pq
