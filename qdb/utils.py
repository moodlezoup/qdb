from typing import List
import networkx as nx
import itertools
from pyquil import Program
from pyquil.quilbase import Gate

from qdb.control_flow_graph import QuilControlFlowGraph


def get_unnecessary_instructions(
    cfg: QuilControlFlowGraph, block_idx: int, qubits: List[int]
) -> List[int]:
    """
    Returns the list of instruction indices that are not necessary to run tomography on
    `qubits` in the basic block `block` for any execution path in `cfg`.
    """
    if len(qubits) == 0:
        return []

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

    entangled_subgraphs = dict(
        [
            (i, cfg.blocks[i].get_local_entangled_graph())
            for i in nx.ancestors(cfg, block_idx)
            | nx.descendants(cfg, block_idx)
            | set([block_idx])
        ]
    )
    # Build the complete graph of dependent qubits with respect to this block
    entangled_graph = nx.compose_all([g for g, _, _ in entangled_subgraphs.values()])
    entangled_edges_across_blocks = [
        (leaf, root)  # Connect qubits across blocks
        for i in entangled_subgraphs.keys()
        for descendant in nx.descendants(cfg, i)
        for root in entangled_subgraphs[i][1]
        for leaf in entangled_subgraphs[descendant][2]
        if root[1] == leaf[1]  # If the qubits of the nodes are the same
    ]
    entangled_graph = nx.compose_all([g for g, _, _ in entangled_subgraphs.values()])
    entangled_graph.add_edges_from(entangled_edges_across_blocks)

    # entangled_graph = cfg.blocks[block_idx].get_local_entangled_graph()
    # for i in nx.ancestors(cfg, block_idx) | nx.descendants(cfg, block_idx):
    #     entangled_graph.add_edges_from(cfg.blocks[i].get_local_entangled_graph().edges)
    # entangled_graph.add_edges_from(dependency_graph.edges)
    # nx.add_path(entangled_graph, set(qubits) | control_flow_dependencies)

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
    necessary_instructions = itertools.chain.from_iterable(
        [
            get_necessary_instructions(cfg, block_index, qubits)
            for block_index in range(len(cfg.blocks))
        ]
    )
    trimmed_program = Program(
        [inst for i, inst in enumerate(pq) if i in necessary_instructions]
    )
    # TODO: Try to remove unused basic blocks and repeat until convergence
    return trimmed_program
