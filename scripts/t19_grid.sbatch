#!/bin/bash
# One T19 evidence job. CPU partition only. No ORCA license and no token.
#SBATCH --job-name=t19-grid
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=t19-grid-%j.out
#SBATCH --error=t19-grid-%j.err

set -euo pipefail
expected="${SPACEOPS_T19_SHA:?set SPACEOPS_T19_SHA to the reviewed commit}"
module load Python/python-3.11.0
source "$HOME/venvs/spaceops-aqt/bin/activate"
python -c "import qiskit_aer; assert qiskit_aer.__version__ == '0.18.2', qiskit_aer.__version__"
cd "$HOME/spaceops-quantum"
actual="$(git rev-parse HEAD)"
if [[ "$actual" != "$expected" ]]; then
  echo "cluster HEAD ${actual} does not match ${expected}"
  exit 2
fi
export SPACEOPS_T19_APPROVED=1
python -m spaceops_quantum.experiment.t19_grid --out "$HOME/t19-grid-v2" --root "$HOME/spaceops-quantum"
