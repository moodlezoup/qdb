# qdb
Breakpoint debugger for pyQuil with inserted tomography

## Installation
Python 3.6 or higher is required.

```bash
git clone git@github.com:mzhu25/qdb.git
cd qdb
python setup.py install
```

This may not install `forest-benchmarking` correctly and a fix is to uninstall it and reinstall it manually with pip.

```bash
pip uninstall forest-benchmarking
pip install forest-benchmarking
```

To run on a QVM, install `quilc` and `qvm` from Rigetti's Forest SDK which can be found at https://www.rigetti.com/forest

## Usage
To run on a QVM, make sure `quilc` and `qvm` are running.

```bash
# Run these commands on two different terminals
quilc -S
qvm -S
```

Let pyQuil know what program to debug by using `qdb.set_trace(qc, pq)` where `qc` is a `pyquil.QuantumComputer` and `pq` is a `pyquil.Program`. Then qdb can step through the construction of `pq` and run tomography with the command `tom [qubit_index [qubit_index...]]`.

## Example
```python
import qdb
from pyquil import Program, get_qc
from pyquil.gates import H, X, Y, Z, CNOT

pq = Program()
pq += H(0)
pq += CNOT(0, 1)
pq += CNOT(1, 2)

qdb.set_trace(get_qc("3q-qvm"), pq)
# 0 1 2 should be in the bell state
```

Running `example.py` with the `qdb.set_trace` line will enter the qdb debugger. Use the `tom` command to get the wavefunction.

```
$ python example.py
--Return--
> example.py(10)<module>()->None
-> qdb.set_trace(get_qc("3q-qvm"), pq)
(Qdb) print_quil
H 0
CNOT 0 1
CNOT 1 2

(Qdb) ent 0
Entanglement set: {0, 1, 2}
(Qdb) tom 0 1 2
# Density matrix displayed here
Purity: (1.0083835+1.143426716157525e-16j)
prob=1.0, Ψ = (0.7-0.01j) |000> + (0.01+0.01j) |011> + 0.01j |101> + (0.03-0.02j) |110> + (0.71+0j) |111>
prob=0.05, Ψ = (-0.07-0.26j) |000> + (-0.2-0j) |001> + (0.63+0j) |010> + (0.14-0.17j) |011> + (0.31+0.02j) |100> + (-0.09+0.28j) |101> + (-0.29-0.32j) |110> + (0.06+0.27j) |111>
prob=0.02, Ψ = (0.11-0j) |000> + (0.64+0j) |001> + (0.08-0.26j) |010> + (-0.27-0.16j) |011> + (0.18+0.48j) |100> + (-0.28-0.15j) |101> + (-0.18-0j) |110> + (-0.1-0j) |111>
prob=0.01, Ψ = (0.35+0.22j) |000> + (-0.21-0.04j) |001> + (0.18-0.34j) |010> + (-0.14+0.34j) |011> + (0.16+0.16j) |100> + (0.43+0j) |101> + (0.06-0.28j) |110> + (-0.36-0.21j) |111>
```

## Testing

```bash
pytest
```
