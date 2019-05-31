import pdb
import sys
import typing
from typing import Any, List

from qdb.control_flow_graph import QuilControlFlowGraph
from qdb.utils import *

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

    def do_entanglement(self, arg: str) -> None:
        """
        CLI wrapper for entanglement_set
        """
        try:
            qubits = [int(x) for x in arg.split()]
        except ValueError:
            self.message("Qubit indices must be specified as a space-separated list")
            return
        self.message(
            "Entanglement set: {}".format(entanglement_set(self.program, qubits))
        )

    do_ent = do_entanglement

    def do_tomography(self, arg: str) -> None:
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
                qubits = list(self.program.get_qubits())
        else:
            try:
                qubits = [int(x) for x in arg.split()]
            except ValueError:
                self.message(
                    "Qubit indices must be specified as a space-separated list"
                )
                return

        experiment = generate_state_tomography_experiment(
            trim_program(self.program, qubits), qubits
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


def set_trace(qc: QuantumComputer, program: Program, header=None):
    qdb = Qdb(qc, program)
    if header is not None:
        qdb.message(header)
    qdb.set_trace(sys._getframe().f_back)
