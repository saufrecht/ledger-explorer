from setuptools import find_packages, setup

setup(
    name="ledgerexplorer",
    version="0.0.1",
    packages=find_packages(include=["ledgex", "ledgex.*"]),
)
