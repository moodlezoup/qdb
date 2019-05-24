import pdb
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
import sys
import typing
from typing import Any, Iterable, List, Set


class Qdb(pdb.Pdb):
    def __init__(
        self,
        qc: QuantumComputer,
        program: Program,
        completekey: str = "tab",
        stdin: Any = None,
        stdout: Any = None,
        skip: Any = None,
        nosigint: bool = False,
        readrc: bool = True,
    ) -> None:
        pdb.Pdb.__init__(
            self,
            completekey=completekey,
            stdin=stdin,
            stdout=stdout,
            skip=skip,
            nosigint=nosigint,
            readrc=readrc,
        )
        self.qc = qc
        self.program = program

    def all_qubits(self):
        """
        Helper function to get all qubit indices that have been acted on by
        gates in the program so far.
        """
        qubits = set()
        for gate in self.program:
            if isinstance(gate, Gate):
                qubits |= set(gate.get_qubits())
        return qubits

    def entanglement_set(self, qubits: Iterable[int]) -> Set[int]:
        """
        Returns a conservative overestimate of the set of qubits entangled with
        one or more of those provided, based entirely on which multi-qubit gates
        have been performed so far.
        """
        entangled_qubits = set(qubits)
        entangled_prev = set()
        while len(entangled_qubits) != len(entangled_prev):
            entangled_prev = entangled_qubits
            for gate in self.program:
                # FIXME: Also check qubit measurements that affect control flow
                if isinstance(gate, Gate):
                    gate_qubits = set(gate.get_qubits())
                    # Here, two qubits are entangled if they share an operator
                    # TODO: Is this a resonable definition?
                    if entangled_qubits & gate_qubits:
                        entangled_qubits |= gate_qubits
        return entangled_qubits

    def do_tomography(self, arg: List[int]) -> None:
        """tom(ography) [qubit_index [qubit_index...]]
        Runs state tomography on the qubits specified by the space-separated
        list of qubit indices. Without argument, run on all qubits in Program
        so far (but first ask confirmation).
        """
        qubits = []
        if not arg:
            try:
                reply = input("Run on all qubits? ")
            except EOFError:
                reply = "no"
            reply = reply.strip().lower()
            if reply in ("y", "yes"):
                qubits = self.all_qubits()
        else:
            try:
                qubits = [int(x) for x in arg.split()]
            except ValueError:
                self.message(
                    "Qubit indices must be specified as a space-separated list"
                )
                return
        self.message("Entanglement set: {}".format(self.entanglement_set(qubits)))

        # TODO: We need to figure out how to use these correctly.
        # settings = [
        #     ExperimentSetting(zeros_state(qubits), gate(qubit))
        #     for qubit in qubits
        #     for gate in [sX, sY, sZ]
        # ]
        # suite = TomographyExperiment(settings, trimmed_pq, qubits)
        # results = measure_observables(qc, group_experiments(suite))
        #
        # TODO: Compute wavefunction amplitudes from measurments
        # for result in results:
        #     results.setting # type ExperimentSetting
        #     results.expectation
        # amplitudes = np.zeros(2**len(qubits))
        # for i in range(len(amplitudes)):
        #     amplitudes[i] = ???
        #
        # return Wavefunction(amplitudes)

    do_tom = do_tomography


def set_trace(qc: QuantumComputer, program: Program, header=None):
    qdb = Qdb(qc, program)
    if header is not None:
        qdb.message(header)
    qdb.set_trace(sys._getframe().f_back)
