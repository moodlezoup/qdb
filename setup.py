from setuptools import setup

setup(
    name="qdb",
    version="0.1",
    description="Breakpoint debugger for pyQuil with inserted tomography",
    url="https://github.com/mzhu25/qdb",
    license="MIT",
    packages=["qdb"],
    install_requires=["pyquil"],
)
