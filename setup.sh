#!/usr/bin/env bash
set -euo pipefail

echo "Setup [0/6]: Checking required system tools..."

missing=()

check_command() {
    if ! command -v "$1" &> /dev/null; then
        missing+=("$1")
    fi
}

check_command "python3"
check_command "pip3"
check_command "perf"
check_command "rocm-smi"

python3 -c "import venv" 2>/dev/null || missing+=("python3-venv")

if (( ${#missing[@]} > 0 )); then
    echo
    echo "Missing required system tools:"
    printf ' - %s\n' "${missing[@]}"
    echo
    echo "Install packages:"
    echo " $ sudo apt install python3 python3-pip python3-venv"
    echo " $ sudo apt install linux-tools-common linux-tools-generic linux-tools-\$(uname -r)"
    echo " $ sudo apt install rocm-smi-lib || sudo apt install rocm-smi"
    exit 1
fi

echo "Setup [1/6]: Creating the virtual environment..."
python3 -m venv .venv || { echo "Failed to create venv"; exit 1; }

echo "Setup [2/6]: Upgrading pip..."
.venv/bin/python -m pip install --upgrade pip

echo "Setup [3/6]: Installing dependencies..."
.venv/bin/python -m pip install -r requirements.txt

echo "Setup [4/6]: Making scripts executable..."
chmod +x scripts/*.sh
chmod +x run.sh

echo "Setup [5/6]: Making Python modules executable..."
chmod +x src/workload_runner.py

echo "Setup [6/6]: Setup complete"
echo
echo "To run a workload, use:"
echo "  $ source .venv/bin/activate"
echo "  $ ./run.sh <workload-runner-path> <workload> [workload-options] [options]"
echo
echo "  Example: $ ./run.sh ./src/workload_runner.py workload -args arg1 -m cpu gpu memory"