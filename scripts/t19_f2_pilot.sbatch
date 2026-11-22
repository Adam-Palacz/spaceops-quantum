#!/bin/bash
# One approved F2 pilot. Do not use this file for the full T19 grid.
#SBATCH --job-name=aqt-f2-pilot
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=aqt-f2-pilot-%j.out
#SBATCH --error=aqt-f2-pilot-%j.err

set -euo pipefail
expected="${SPACEOPS_PILOT_SHA:?set SPACEOPS_PILOT_SHA to the reviewed commit}"
module load Python/python-3.11.0
source "$HOME/venvs/spaceops-aqt/bin/activate"
python -c "import qiskit_aer; assert qiskit_aer.__version__ == '0.18.2', qiskit_aer.__version__"
cd "$HOME/spaceops-quantum"
actual="$(git rev-parse HEAD)"
if [[ "$actual" != "$expected" ]]; then
  echo "cluster HEAD ${actual} does not match ${expected}"
  exit 2
fi
python -m spaceops_quantum.experiment.f2_pilot \
  --scenario configs/f2_six_tasks.yaml \
  --out "$HOME/aqt-f2-pilot-seed0"
