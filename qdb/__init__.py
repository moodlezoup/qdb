from pyquil import Program
from pyquil.quilbase import Gate, Nop
from pyquil.operator_estimation import (
    TomographyExperiment,
    group_experiments,
    measure_observables,
    ExperimentSetting,
    zeros_state,
)
from pyquil.paulis import sX, sY, sZ
from pyquil.api import QuantumComputer


class Breakpoint(Nop):
    def __init__(self, qubits):
        Nop.__init__(self)
        self.qubits = qubits


# TODO: Move to another file
def trim_to_breakpoint(pq: Program) -> Program:
    """
    Removes all qubits and instructions that the breakpoint does not depend on.
    """
    breakpoints = [gate for gate in pq if isinstance(gate, Breakpoint)]
    if len(breakpoints) != 1:
        raise ValueError("Program must have exactly one breakpoint")
    entangled_qubits = set(breakpoints[0].qubits)
    entangled_prev = set()
    while len(entangled_qubits) != len(entangled_prev):
        entangled_prev = entangled_qubits
        for gate in pq:
            # FIXME: Also check qubit measurements that affect control flow
            if isinstance(gate, Gate):
                gate_qubits = set(gate.get_qubits())
                # Here, two qubits are entangled if they share an operator
                # TODO: Is this a resonable definition?
                if entangled_qubits & gate_qubits:
                    entangled_qubits |= gate_qubits
    # TODO: Remove jump statements that do nothing
    trimmed_pq = Program(
        [
            gate
            for gate in pq
            if not isinstance(gate, Gate) or entangled_qubits & set(gate.get_qubits())
        ]
    )
    return trimmed_pq


# TODO: It would be nice if this returned a Wavefunction, but maybe that isn't possible
# def debug(qc: QuantumComputer, pq: Program) -> Wavefunction:
def debug(qc: QuantumComputer, pq: Program):
    trimmed_pq = trim_to_breakpoint(pq)

    qubits = list(trimmed_pq.get_qubits())

    # TODO: We need to figure out how to use these correctly.
    settings = [
        ExperimentSetting(zeros_state(qubits), gate(qubit))
        for qubit in qubits
        for gate in [sX, sY, sZ]
    ]
    suite = TomographyExperiment(settings, trimmed_pq, qubits)
    results = measure_observables(qc, group_experiments(suite))

    # TODO: Compute wavefunction amplitudes from measurments
    # for result in results:
    #     results.setting # type ExperimentSetting
    #     results.expectation
    # amplitudes = np.zeros(2**len(qubits))
    # for i in range(len(amplitudes)):
    #     amplitudes[i] = ???
    #
    # return Wavefunction(amplitudes)

    return results
