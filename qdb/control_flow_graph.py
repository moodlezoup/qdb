from typing import List
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


# TODO: Remove basic blocks that are not in `nx.descendants(G, "root")` and that
#       might reduce the entangled set.
def get_control_flow_graph(pq: Program) -> (nx.DiGraph, List[Program]):
    """Constructs the control flow graph for program `pq`."""
    targets = {}
    """
    A basic block is a sequence of instructions such that if one instruction is
    executed then all are guaranteed to execute.
    """
    basic_blocks = []
    block = []
    for inst in pq:
        if isinstance(inst, JumpTarget):
            if block:
                basic_blocks.append(block)
            block = [inst]
            targets[inst.label] = len(basic_blocks)  # The index of the next basic block
        elif isinstance(inst, (Jump, JumpConditional, Halt)):
            basic_blocks.append(block + [inst])
            block = []
        elif is_fallthrough_instruction(inst):
            block.append(inst)
        else:
            raise ValueError(f"Unhandled instruction type {type(inst)} for {inst}")
    if block:
        basic_blocks.append(block)

    edges = [("root", 0)]
    for block_idx in range(len(basic_blocks) - 1):
        inst = basic_blocks[block_idx][-1]  # The last instruction in the basic block
        if is_fallthrough_instruction(inst):
            edges.append((block_idx, block_idx + 1))
        elif isinstance(inst, Jump):
            edges.append((block_idx, targets[inst.target]))
        elif isinstance(inst, JumpConditional):
            edges.append((block_idx, block_idx + 1))
            edges.append((block_idx, targets[inst.target]))
        elif isinstance(inst, Halt):
            pass
        else:
            raise ValueError(f"Unhandled instruction type {type(inst)} for {inst}")

    return nx.DiGraph(edges), basic_blocks


def is_dag(pq: Program) -> bool:
    """Returns true if the control flow graph of `pq` is a dag."""
    G, _ = get_control_flow_graph(pq)
    return nx.is_directed_acyclic_graph(G)
