import pdb
import sys
import typing
from typing import Any, Iterable, List, Set

from forest.benchmarking.tomography import *
from pyquil import Program
from pyquil.api import QuantumComputer
from pyquil.operator_estimation import measure_observables
from pyquil.paulis import sX, sY, sZ
from pyquil.quilbase import Gate, Nop


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
        self.prompt = "(Qdb) "

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

    def entanglement_set(self, qubits: List[int]) -> Set[int]:
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

    def do_entanglement(self, arg: List[int]) -> None:
        """
        CLI wrapper for entanglement_set
        """
        try:
            qubits = [int(x) for x in arg.split()]
        except ValueError:
            self.message("Qubit indices must be specified as a space-separated list")
            return
        self.message("Entanglement set: {}".format(self.entanglement_set(qubits)))

    do_ent = do_entanglement

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

        experiment = generate_state_tomography_experiment(
            self.trim_program(qubits), qubits
        )
        # TODO: Let user specify n_shots (+ other params)
        results = list(
            measure_observables(qc=self.qc, tomo_experiment=experiment, n_shots=1000)
        )
        # TODO: Let user specify algorithm
        rho_est = linear_inv_state_estimate(results, qubits)
        self.message(np.round(rho_est, 4))
        self.message("Purity: {}".format(np.trace(np.matmul(rho_est, rho_est))))

    do_tom = do_tomography

    def trim_program(self, qubits: List[int]) -> Program:
        entangled_qubits = self.entanglement_set(qubits)
        trimmed_program = Program()
        for gate in self.program:
            if isinstance(gate, Gate):
                gate_qubits = set(gate.get_qubits())
                if entangled_qubits & gate_qubits:
                    trimmed_program += gate
        return trimmed_program


def set_trace(qc: QuantumComputer, program: Program, header=None):
    qdb = Qdb(qc, program)
    if header is not None:
        qdb.message(header)
    qdb.set_trace(sys._getframe().f_back)
