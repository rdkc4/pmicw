#!/usr/bin/env bash
set -euo pipefail

echo "Setup [0/9]: Checking required system tools..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

bpftrace_ok=false
if command -v bpftrace &>/dev/null; then
    ver=$(bpftrace --version | head -n1 | awk '{print $2}' | sed 's/v//')
    required="0.26.0"

    dpkg --compare-versions "$ver" ge "$required" && bpftrace_ok=true
fi

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

if [ "$bpftrace_ok" = false ]; then
    apt_packages+=(
        "libelf-dev" "clang" "llvm-dev" "libclang-dev" 
        "libcereal-dev" "dwarves" "git" "cmake"
        "ninja-build" "libbpf-dev" "zlib1g-dev"
        "googletest" "libgtest-dev" "libgmock-dev"
        "libpolly-18-dev"
    )
fi

echo "Setup [1/9]: Installing required system tools..."
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

echo "Setup [2/9]: Building bpftrace..."
if [ "$bpftrace_ok" = false ]; then
    (
        rm -rf bcc
        git clone --recursive https://github.com/iovisor/bcc.git
        
        mkdir bcc/build && cd bcc/build
        cmake -DCMAKE_BUILD_TYPE=Release ..

        make -j$(nproc)
        sudo make install
    )
    sudo rm -rf bcc
    (   
        rm -rf bpftrace
        git clone https://github.com/bpftrace/bpftrace.git
        
        cd bpftrace
        git checkout v0.26.0
        git submodule update --init --recursive

        mkdir build && cd build
        cmake -DCMAKE_BUILD_TYPE=Release ..

        make -j$(nproc)
        sudo make install

        sudo ln -sf /usr/local/bin/bpftrace /usr/bin/bpftrace
    )
    sudo rm -rf bpftrace
else
    echo "bpftrace 0.26+ is already installed"
fi

echo "Setup [3/9]: Creating the virtual environment..."
python3 -m venv .venv || { echo "Failed to create venv"; exit 1; }

echo "Setup [4/9]: Upgrading pip..."
.venv/bin/python -m pip install --upgrade pip

echo "Setup [5/9]: Installing dependencies..."
.venv/bin/python -m pip install -r requirements.txt

echo "Setup [6/9]: Making scripts executable..."
chmod +x scripts/*.sh
chmod +x run.sh

echo "Setup [7/9]: Making Python modules executable..."
chmod +x src/workload_runner.py
chmod +x src/comparison_tool.py
chmod +x workloads/test*

echo "Setup [8/9]: Setting sysctl variable..."
sudo sysctl -w kernel.perf_event_paranoid=1

echo "Setup [9/9]: Setup complete"
echo
echo "To run a workload, use:"
echo "  $ source .venv/bin/activate"
echo "  $ ./run.sh [options] <workload> [workload-args...]"
echo
echo "  Example: $ ./run.sh -cmp 10 -rfmt csv,md,json -vfmt chart,table,graph -m cpu,gpu,memory workload"