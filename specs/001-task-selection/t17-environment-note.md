# T17 environment note — login shell, 2026-11-17

Status: package check closed. Python 3.11 loads, and that interpreter has no Qiskit and no AQT provider. Emulator access is not confirmed. No job was submitted and nothing was installed.

The check ran in the existing SSH login shell, inside a clone of this repository. Account names, host names, and any token values are omitted.

| Fact | Observed |
|---|---|
| Git commit | `fb8a97f4b593624de96b22033f03877995cb86e4` |
| Branch | `main`, even with `origin/main` |
| Python on `PATH` | 3.9.18, `/usr/bin/python3` and `/usr/bin/python3.9` |
| Environment modules | `module` is installed. `conda` and `uv` are absent from `PATH` |
| Visible module names | `Python/python-3.11.0` is available. No module name matched `qiskit`, `aqt`, or `quantum`. `CMake/3.30.3` and `gcc/14.2.0-x86_64` appeared on the same listing row |
| Python 3.11 module | `module load Python/python-3.11.0` succeeds. Interpreter is Python 3.11.0 at `/opt/python/3.11.0/bin/python3` |
| `qiskit` | not installed in Python 3.9 or in this Python 3.11 |
| `qiskit-aer` | not installed in Python 3.9 or in this Python 3.11 |
| `qiskit-aqt-provider` | not installed in Python 3.9 or in this Python 3.11 |
| `AQT_TOKEN` or `AQT_ACCESS_TOKEN` | unset in both checks |
| Provider import | `ModuleNotFoundError` on Python 3.9 and on Python 3.11 |
| Backend name, native gates, qubit count, shot limit, job limit | not observed |

Local pins remain `qiskit==2.4.1` and `qiskit-aer==0.18.2`. The 3.11 module matches the language requirement and its site-packages do not contain the quantum stack. `AQTProvider()` was not constructed. Installing packages on the login shell was not part of this check.

Claimed ceilings of 200 shots per circuit, about 50 circuits per job, and native R, RZ, and RXX gates stay unverified. T18 and T19 stay closed.

## Login access on 2026-11-19

An interactive WSL terminal reached the login shell. Account names, addresses, and passwords are omitted. No job was submitted and nothing was installed.

| Fact | Observed |
|---|---|
| SSH alias | `quantum` in the Windows SSH config. The config has no identity file |
| Remote prompt name | `quantum-ui`. This is the shell name, not the SSH alias |
| Non-interactive `wsl ssh` | refused: `Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password)`. A new command cannot reuse the password session |
| Login message | Documents two ORCA quantum computers, reached with Slurm licenses `orca1` and `orca2`. It does not mention AQT, Qiskit, or an emulator |
| Slurm commands | `sbatch`, `sinfo`, `scontrol`, and `sacctmgr` respond |
| Partition `all` | default partition, availability up: 1 node `mixed`, 4 nodes `idle` |
| Slurm licenses | `scontrol show lic` reports `No licenses configured in Slurm` |
| Accounting association | two rows, both account `root`, QOS `normal`, with empty group limits and empty max jobs. The interactive user is not named |
| CPU dry run | `sbatch --test-only --wrap=true -p all` did not launch a job. Slurm estimated job 2062 would start at 2026-11-19T11:47:37 on `quantum-cpu-01`, using 2 processors |
| Disk | `CLUSTER_README` states a 100G default user quota. `/scratch` is described as having no quota |
| `CLUSTER_README` | Repeats the ORCA license instructions. A search for AQT, Qiskit, PIAST, and emulator returned no match |
| System Pythons | 3.9 and the `Python/python-3.11.0` module still have no Qiskit and no AQT provider |
| Private environment | `$HOME/venvs/spaceops-aqt` has `qiskit` 2.4.1 and `qiskit-aqt-provider` 2.0.1 |

The login documents name ORCA licenses `orca1` and `orca2`, while the Slurm controller has no licenses configured. The dry run only shows that a CPU task on partition `all` would be accepted. It does not show an ORCA device, an AQT backend, native gates, a shot limit, or a quantum allocation. T18 and T19 stay closed.

## Offline AQT job 2063

A private virtual environment at `$HOME/venvs/spaceops-aqt` supplied `qiskit-aqt-provider`. Job 2063 used partition `all`, 2 CPUs, 4G, and a 15-minute limit. It did not request an ORCA license or a token. Slurm reports state `FAILED`, exit `1:0`, elapsed `00:00:01`.

Standard output printed `qiskit 2.4.1`. Standard error is `AttributeError: module 'qiskit_aqt_provider' has no attribute '__version__'`. The import of the provider module succeeded. `offline.ideal()` and `offline.noisy()` were not called. No remote QPU was contacted. The script's version line is the failure, so this run does not measure the offline backends.

## Offline AQT job 2064

The same script, with the version read from package metadata, was submitted as job 2064. Resources were unchanged: partition `all`, 2 CPUs, 4G, 15 minutes, no ORCA license, no token. Slurm reports state `COMPLETED`, exit `0:0`, elapsed `00:00:01`. Standard error is empty.

| Backend call | Resource id | 100-shot counts |
|---|---|---|
| `offline.ideal()` | `offline_simulator_no_noise` | `00`: 47, `11`: 53 |
| `offline.noisy()` | `offline_simulator_noise` | `00`: 43, `11`: 57 |

Both calls printed `success`. The samples contain only the Bell outcomes `00` and `11`. These are the provider's local simulators running on an HPC CPU node. The run did not contact a remote QPU, did not list native hardware gates, and did not read an emulator shot limit or a quantum allocation. T17 stays open for those facts. T18 and T19 stay closed.
