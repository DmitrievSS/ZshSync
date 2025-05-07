from setuptools import setup, find_packages

setup(
    name="zsh_sync",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'paramiko',
        'gitpython',
    ],
) 