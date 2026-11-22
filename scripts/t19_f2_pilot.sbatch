#!/bin/bash
# Not submitted. One F2 pilot only, after explicit approval.
# This file does not start the 6-scenario T19 grid and does not call a QPU.
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
echo "F2 pilot is not approved for execution in this review"
exit 2
