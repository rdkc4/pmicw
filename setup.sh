#!/usr/bin/env bash
set -euo pipefail

echo "Setup [0/5]: Creating the virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Setup [1/5]: Upgrading pip..."
pip install --upgrade pip

echo "Setup [2/5]: Installing dependencies..."
pip install -r requirements.txt

echo "Setup [3/5]: Making scripts executable..."
chmod +x scripts/*.sh
chmod +x run.sh

echo "Setup [4/5]: Making Python modules executable..."
chmod +x src/workload_runner.py

echo "Setup [5/5]: Setup complete"
echo
echo "To run a workload, use the following commands:"
echo "source .venv/bin/activate"
echo "Usage: ./run.sh <workload-runner-path> <workload> [workload-options] [options]"
echo "Example: ./run.sh ./src/workload_runner.py workload -args arg1 -m cpu gpu memory"