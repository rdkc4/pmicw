#!/usr/bin/env bash
set -euo pipefail

echo "Setup [0/7]: Checking required system tools..."

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
check_command "jq"

python3 -c "import venv" 2>/dev/null || missing+=("python3-venv")

apt_packages=()

for cmd in "${missing[@]}"; do
    case "$cmd" in
        python3)      apt_packages+=("python3" "python3-pip" "python3-venv") ;;
        pip3)         apt_packages+=("python3-pip") ;;
        python3-venv) apt_packages+=("python3-venv") ;;
        jq)           apt_packages+=("jq") ;;
        perf)         apt_packages+=("linux-tools-common" "linux-tools-generic" "linux-tools-$(uname -r)") ;;
        rocm-smi)     apt_packages+=("rocm-smi")
    esac
done

echo "Setup [1/7]: Installing required system tools..."
if (( ${#apt_packages[@]} > 0 )); then
    unique_packages=($(echo "${apt_packages[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '))
    
    echo
    echo "Missing dependencies found. Attempting automatic installation..."
    echo "Packages to install: ${unique_packages[*]}"
    echo
    
    sudo apt-get update -y
    sudo apt-get install -y "${unique_packages[@]}"
else
    echo "All system tools are already installed."
fi

echo "Setup [2/7]: Creating the virtual environment..."
python3 -m venv .venv || { echo "Failed to create venv"; exit 1; }

echo "Setup [3/7]: Upgrading pip..."
.venv/bin/python -m pip install --upgrade pip

echo "Setup [4/7]: Installing dependencies..."
.venv/bin/python -m pip install -r requirements.txt

echo "Setup [5/7]: Making scripts executable..."
chmod +x scripts/*.sh
chmod +x run.sh

echo "Setup [6/7]: Making Python modules executable..."
chmod +x src/workload_runner.py
chmod +x src/comparison_tool.py
chmod +x workloads/test*

echo "Setup [7/7]: Setup complete"
echo
echo "To run a workload, use:"
echo "  $ source .venv/bin/activate"
echo "  $ ./run.sh [options] <workload> [workload-args...]"
echo
echo "  Example: $ ./run.sh -rfmt csv,md,json -m cpu,gpu,memory workload arg1 arg2"