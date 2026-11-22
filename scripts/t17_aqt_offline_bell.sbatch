#!/bin/bash
#SBATCH --job-name=aqt-offline-bell
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=aqt-offline-bell-%j.out
#SBATCH --error=aqt-offline-bell-%j.err

set -euo pipefail
cd "$HOME/aqt-offline-bell"
module load Python/python-3.11.0
source "$HOME/venvs/spaceops-aqt/bin/activate"
python "$HOME/aqt-offline-bell/t17_aqt_offline_bell.py"
