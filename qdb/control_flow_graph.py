from typing import List, Set, NamedTuple
import networkx as nx

from pyquil import Program
from pyquil.quilbase import (
    AbstractInstruction,
    Gate,
    Declare,
    Measurement,
    UnaryClassicalInstruction,
    LogicalBinaryOp,
    ArithmeticBinaryOp,
    ClassicalExchange,
    ClassicalConvert,
    ClassicalLoad,
    ClassicalStore,
    ClassicalComparison,
    Jump,
    JumpConditional,
    JumpTarget,
    Halt,
    ResetQubit,
    Nop,
    MemoryReference,
)


class QuilBlock(NamedTuple):
    """
    A basic block is a sequence of instructions such that if one instruction is
    executed then all are guaranteed to execute.

    Attributes
    ----------
    start_index : int
        The index of the first instruction in the basic block (with respect to the
        original program)
    body : List[AbstractInstruction]
        A list of non-control-flow instructions for this basic block
    out_edges : List[AbstractInstruction]
        A list of control flow instruction at the end of this basic block
    """

    start_index: int
    body: List[AbstractInstruction]
    out_edges: List[AbstractInstruction]

    def __repr__(self) -> str:
        inst_strs = [str(inst) for inst in self.body + self.out_edges]
        width = max([len(inst_str) for inst_str in inst_strs])
        pretty = "\n+-" + "-" * width + "-+\n"
        for inst_str in inst_strs:
            pretty += "| " + inst_str.ljust(width) + " |\n"
        pretty += "+-" + "-" * width + "-+"
        return pretty

    def get_local_entangled_graph(self) -> nx.Graph:
        """Returns the graph of entangled qubits considering only this basic block"""
        entangled_graph = nx.Graph()
        for inst in self.body:
            if isinstance(inst, Gate):
                nx.add_path(entangled_graph, inst.get_qubits())
        return entangled_graph

    def get_local_control_flow_qubits(self) -> Set[int]:
        """Returns a set of qubits that determine this block's control flow"""
        bits = list(self.get_control_flow_bits())
        if len(bits) == 0:
            return set()

        dependency_graph = self.get_local_dependency_graph()
        nx.add_path(dependency_graph, bits)

        dependency_graph.add_edges_from(self.get_local_entangled_graph().edges)
        if len(dependency_graph.edges) == 0:
            return set(bits)
        return set(
            [i for i in nx.dfs_tree(dependency_graph, bits[0]) if isinstance(i, int)]
        )

    def get_local_dependency_graph(self) -> nx.Graph:
        """
        Returns the graph of entangled qubits and classical bits that determine this
        block's control flow
        """
        dependency_graph = nx.Graph()
        for inst in self.body:
            if isinstance(inst, LogicalBinaryOp):
                dependency_graph.add_edge(inst.left, inst.right)
            elif isinstance(inst, ArithmeticBinaryOp):
                if isinstance(inst.right, MemoryReference):
                    dependency_graph.add_edge(inst.left, inst.right)
            elif isinstance(inst, Measurement):
                dependency_graph.add_edge(inst.classical_reg, inst.qubit.index)
        return dependency_graph

    def get_control_flow_bits(self) -> Set[MemoryReference]:
        """
        Returns the set of classical bits that directly affect control flow of this
        basic block
        """
        return set(
            [
                inst.condition
                for inst in self.out_edges
                if isinstance(inst, JumpConditional)
            ]
        )


class QuilControlFlowGraph(nx.DiGraph):
    def __init__(self, program: Program) -> None:
        self.program = program
        self.blocks = []
        nx.DiGraph.__init__(self)
        self._build_cfg()

    def __repr__(self) -> str:
        return "\n".join(str(b) for b in self.blocks)

    __str__ = __repr__

    def _build_cfg(self) -> None:
        """Constructs the control flow graph for the program."""

        start_index = 0
        body = []
        targets = {}

        for idx, inst in enumerate(self.program):
            if isinstance(inst, JumpTarget):
                if body:
                    self.blocks.append(QuilBlock(start_index, body, []))
                # Next block is the jump target
                body = [inst]
                start_index = idx
                targets[inst.label] = len(self.blocks)

            # Handles the case where we have multiple Jump(Conditional)s in a row:
            # we want to treat this as multiple out-edges from a single node.
            elif isinstance(inst, (Jump, JumpConditional, Halt)):
                if body:
                    self.blocks.append(QuilBlock(start_index, body, []))
                    body = []
                    start_index = idx + 1
                self.blocks[-1].out_edges.append(inst)

            elif is_fallthrough_instruction(inst):
                body.append(inst)
            else:
                raise ValueError(f"Unhandled instruction type {type(inst)} for {inst}")

        if body:
            self.blocks.append(QuilBlock(start_index, body, []))

        assert len(self.program) == sum(
            len(b.body) + len(b.out_edges) for b in self.blocks
        )
        if len(self.blocks) == 0:
            return
        else:
            self.add_nodes_from(range(len(self.blocks)))

        for block_idx, block in enumerate(self.blocks):
            if not block.out_edges and (block_idx + 1) in self.nodes:
                self.add_edge(block_idx, block_idx + 1)
            else:
                for inst in block.out_edges:
                    if isinstance(inst, Jump):
                        # Handles case where jump target is the end of the program
                        if targets[inst.target] in self.nodes:
                            self.add_edge(block_idx, targets[inst.target])
                    elif isinstance(inst, JumpConditional):
                        if (block_idx + 1) in self.nodes:
                            self.add_edge(block_idx, block_idx + 1)
                        if targets[inst.target] in self.nodes:
                            self.add_edge(
                                block_idx,
                                targets[inst.target],
                                condition=inst.condition,
                            )
                    else:
                        pass

    def is_dag(self) -> bool:
        """Returns true if the control flow graph is a dag."""
        return nx.is_directed_acyclic_graph(self)


def is_fallthrough_instruction(inst: AbstractInstruction) -> bool:
    """Returns true if `inst` is an instruction that is guaranteed to fallthrough."""
    return isinstance(
        inst,
        (
            Gate,
            Declare,
            Measurement,
            UnaryClassicalInstruction,
            LogicalBinaryOp,
            ArithmeticBinaryOp,
            ClassicalExchange,
            ClassicalConvert,
            ClassicalLoad,
            ClassicalStore,
            ClassicalComparison,
            JumpTarget,
            ResetQubit,
            Nop,
        ),
    )
