from setuptools import setup, find_packages

setup(
    name='ledgerexplorer',
    version='0.0.1',
    packages=find_packages(include=['ledgex', 'ledgex.*'])
)
