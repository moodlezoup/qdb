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

    start_index: int  # TODO: Not really used yet
    body: List[AbstractInstruction]
    out_edges: List[AbstractInstruction]
    # TODO: Maybe add a `label` (JumpTarget) attribute if useful

    def __repr__(self) -> str:
        inst_strs = [str(inst) for inst in self.body]
        width = max([len(inst_str) for inst_str in inst_strs])
        pretty = "\n+-" + "-" * width + "-+\n"
        for inst_str in inst_strs:
            pretty += "| " + inst_str.ljust(width) + " |\n"
        pretty += "+-" + "-" * width + "-+"
        return pretty


class QuilControlFlowGraph(nx.DiGraph):
    def __init__(self, program: Program) -> None:
        self.program = program
        self.blocks = []
        nx.DiGraph.__init__(self)
        self._build_cfg()

    # TODO: Remove basic blocks that are not in `nx.descendants(G, "root")` and that
    #       might reduce the entangled set.
    def _build_cfg(self) -> None:
        """Constructs the control flow graph for the program."""

        current_block = QuilBlock(start_index=0, body=[], out_edges=[])
        targets = {}

        for idx, inst in enumerate(self.program):
            if isinstance(inst, JumpTarget):
                if current_block.body:
                    self.blocks.append(current_block)
                # Next block is the jump target
                current_block = QuilBlock(start_index=0, body=[], out_edges=[])
                targets[inst.label] = len(self.blocks)

            # Handles the case where we have multiple Jump(Conditional)s in a row:
            # we want to treat this as multiple out-edges from a single node.
            elif isinstance(inst, (Jump, JumpConditional, Halt)):
                if current_block.body:
                    self.blocks.append(current_block)
                    current_block = QuilBlock(start_index=0, body=[], out_edges=[])
                self.blocks[-1].out_edges.append(inst)

            elif is_fallthrough_instruction(inst):
                current_block.body.append(inst)
            else:
                raise ValueError(f"Unhandled instruction type {type(inst)} for {inst}")

        if current_block.body:
            self.blocks.append(current_block)
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
