# qdb
Breakpoint debugger for pyQuil with inserted tomography

## Installation
Python 3.6 or higher is required.

```
git clone git@github.com:mzhu25/qdb.git
cd qdb
python setup.py install
```

This may not install `forest-benchmarking` correctly and a fix is to uninstall it and reinstall it manually with pip.

```
pip uninstall forest-benchmarking
pip install forest-benchmarking
```

To run on a QVM, install `quilc` and `qvm` from Rigetti's Forest SDK which can be found at https://www.rigetti.com/forest

## Usage
To run on a QVM, make sure `quilc` and `qvm` are running.

```
# Run these commands on two different terminals
quilc -S
qvm -S
```

Let pyQuil know what program to debug by using `qdb.set_trace(qc, pq)` where `qc` is a `pyquil.QuantumComputer` and `pq` is a `pyquil.Program`. Then qdb can step through the construction of `pq` and run tomography when asked.

```
$ python sandbox.py
> /.../sandbox.py(12)<module>()
-> pq += H(0)
(Qdb) n
> /.../sandbox.py(13)<module>()
-> pq += CNOT(0, 1)
(Qdb) n
--Return--
> /.../sandbox.py(13)<module>()->None
-> pq += CNOT(0, 1)
(Qdb) tom 0 1
0.707 * |00> + 0.707 * |11>
```

## Testing

```
pytest
```
