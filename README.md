# py-kvm

This module aims to manage KVM hypervisors. For this it use the unix module which allow to manage Unix-like systems, both locally and remotely, in the same by overloading class instances.

## Usage

```python
>>> from unix import Local, Remote, UnixError
>>> from unix.linux import Linux
>>> from kvm.hypervisor import Hypervisor
>>> import json

>>> localhost = Hypervisor(Linux(Local()))
>>> localhost.hypervisor.nodeinfo()

{'nb_cpu': 1,
 'nb_threads_per_core': 2,
 'memory': 16331936,
 'numa_cells': 1,
 'cpu_model': 'x86_64',
 'nb_cores_per_cpu': 4,
 'nb_cores': 8,
 'cpu_freq': 1340}

>>> localhost.list_domains(all=True)

{'guest1': {'id': -1, 'state': 'shut off'}}
{'guest2': {'id': 1, 'state': 'running'}}

```