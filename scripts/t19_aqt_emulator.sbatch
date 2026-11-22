#!/bin/bash
# Not submitted. The full T19 grid is not approved.
# The next proposed job is scripts/t19_f2_pilot.sbatch.
#SBATCH --job-name=aqt-emulator-plan
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=aqt-emulator-plan-%j.out
#SBATCH --error=aqt-emulator-plan-%j.err

set -euo pipefail
echo "T19 grid is not approved"
exit 2
