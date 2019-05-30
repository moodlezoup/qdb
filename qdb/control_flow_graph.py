from typing import List, NamedTuple
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
)


class QuilBlock(NamedTuple):
    """
    A basic block is a sequence of instructions such that if one instruction is
    executed then all are guaranteed to execute.
    """

    body: List[AbstractInstruction]
    out_edges: List[AbstractInstruction]
    start_index: int

    def __repr__(self) -> str:
        inst_strs = [str(inst) for inst in body]
        width = max([len(inst_str) in inst_strs])
        pretty = "+-" + "-" * width + "-+\n"
        for inst_str in inst_strs:
            pretty += "| " + inst_str.ljust(width) + " |\n"
        pretty += "+-" + "-" * width + "-+"
        return pretty


class QuilControlFlowGraph(nx.DiGraph):
    def __init__(self, qc: QuantumComputer, program: Program) -> None:
        self.qc = qc
        self.program = program
        self.blocks = [QuilBlock([], start_index=-1, is_root=True)]
        nx.DiGraph.__init__(self)
        self._build_cfg()

    # TODO: Remove basic blocks that are not in `nx.descendants(G, "root")` and that
    #       might reduce the entangled set.
    def _build_cfg(self) -> None:
        """Constructs the control flow graph for the program."""

        current_block = QuilBlock([], 0)
        targets = {}

        for idx, inst in enumerate(self.program):
            if isinstance(inst, JumpTarget):
                if current_block.instructions:
                    self.blocks.append(current_block)
                # Next block is the jump target
                current_block = QuilBlock([], idx)
                targets[inst.label] = len(self.blocks)

            # Handles the case where we have multiple Jump(Conditional)s in a row:
            # we want to treat this as multiple out-edges from a single node.
            elif isinstance(inst, (Jump, JumpConditional, Halt)):
                if current_block.instructions:
                    self.blocks.append(current_block)
                    current_block = QuilBlock([], idx)
                self.blocks[-1].out_edges.append(inst)

            elif is_fallthrough_instruction(inst):
                current_block.instructions.append(inst)
            else:
                raise ValueError(f"Unhandled instruction type {type(inst)} for {inst}")

        if current_block.instructions:
            self.blocks.append(current_block)
        if len(self.blocks) == 0:
            return

        for block_idx, block in enumerate(self.blocks[:-1]):
            if not block.out_edges:
                edges.append((block_idx, block_idx + 1))
            else:
                for inst in block.out_edges:
                    if isinstance(inst, Jump):
                        edges.append((block_idx, targets[inst.target]))
                    elif isinstance(inst, JumpConditional):
                        edges.append((block_idx, block_idx + 1))
                        edges.append(
                            (
                                block_idx,
                                targets[inst.target],
                                {"condition": inst.condition},
                            )
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
