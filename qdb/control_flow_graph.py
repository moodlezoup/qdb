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
    ClassicalMove,
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
        """
        Returns the directed graph of entangled qubits considering only this basic
        block. Nodes are a tuple of qubits and instruction indices. There are directed
        edges so that if qubit A depends on qubit B then there is a path from A to B.
        This is accomplished by the following rules:

        1. There are directed edges between all qubits within a multi-qubit gate.
        2. There is a directed edge from two nodes that share a qubit that goes from
           the later gate to the earlier gate if that qubit is not measured between
           them.
        """
        entangled_graph = nx.DiGraph()
        instructions = list(enumerate(self.body, start=self.start_index))
        for indexB, instB in instructions:
            if isinstance(instB, Gate):
                qubits = instB.get_qubits()
                if len(qubits) > 1:
                    nodes = [(indexB, q) for q in qubits]
                    nx.add_path(entangled_graph, nodes + [nodes[0]])
                for indexA, instA in instructions[indexB + 1 - self.start_index :]:
                    if isinstance(instA, Gate):
                        entangled_graph.add_edges_from(
                            [
                                ((indexA, q), (indexB, q))
                                for q in instA.get_qubits()
                                if q in qubits
                            ]
                        )
                    elif isinstance(instA, Measurement) and instA.qubit.index in qubits:
                        qubits.remove(instA.qubit.index)
                        entangled_graph.add_edge(
                            (indexA, instA.qubit.index), (indexB, instA.qubit.index)
                        )

        return entangled_graph

    def get_local_dependency_graph(self) -> nx.Graph:
        """
        Returns the directed graph of dependent classical bits and their corresponding
        qubits that determine this block's control flow
        """
        edges = []
        instructions = [
            (index, inst)
            for index, inst in enumerate(self.body, start=self.start_index)
        ]
        for i, (indexB, instB) in enumerate(instructions):
            if isinstance(instB, Measurement):
                register = instB.classical_reg
                edges.append(((indexB, register), (indexB, instB.qubit.index)))
            elif isinstance(instB, UnaryClassicalInstruction):
                register = instB.target
            elif isinstance(
                instB,
                (
                    LogicalBinaryOp,
                    ArithmeticBinaryOp,
                    ClassicalMove,
                    ClassicalExchange,
                    ClassicalConvert,
                ),
            ):
                register = instB.left
                if isinstance(instB.right, MemoryReference):
                    edges.append(((indexB, register), (indexB, instB.right)))
            elif isinstance(instB, ClassicalLoad):
                register = instB.target
                edges.append(((indexB, register), (indexB, instB.right)))
                if isinstance(instB.left, MemoryReference):
                    edges.append(((indexB, register), (indexB, instB.left)))
            elif isinstance(instB, ClassicalStore):
                register = instB.target
                edges.append(((indexB, register), (indexB, instB.left)))
                if isinstance(instB.right, MemoryReference):
                    edges.append(((indexB, register), (indexB, instB.right)))
            elif isinstance(instB, ClassicalComparison):
                register = instB.target
                edges.append(((indexB, register), (indexB, instB.left)))
                if isinstance(instB.right, MemoryReference):
                    edges.append(((indexB, register), (indexB, instB.right)))
            else:
                continue
            assert isinstance(register, MemoryReference)

            for indexA, instA in instructions[i + 1 :]:
                if isinstance(instA, Measurement) and register == instA.classical_reg:
                    break
                elif (
                    isinstance(
                        instA,
                        (
                            LogicalBinaryOp,
                            ArithmeticBinaryOp,
                            ClassicalMove,
                            ClassicalExchange,
                            ClassicalConvert,
                        ),
                    )
                    and register == instA.right
                ):
                    edges.append(((indexA, register), (indexB, register)))
                elif isinstance(
                    instA, (ClassicalLoad, ClassicalStore, ClassicalComparison)
                ) and register in (instA.right, instA.left):
                    edges.append(((indexA, register), (indexB, register)))

        return nx.DiGraph(edges)

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
            ClassicalMove,
            ClassicalLoad,
            ClassicalStore,
            ClassicalComparison,
            JumpTarget,
            ResetQubit,
            Nop,
        ),
    )
