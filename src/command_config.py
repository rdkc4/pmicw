from dataclasses import dataclass, field
import os
import sys
import yaml

@dataclass
class RocmSMICommandConfig:
    base_command: list
    device_flag:  str
    device_index: int

@dataclass
class PerfCommandConfig:
    base_command: list

@dataclass
class CommandConfig:
    rocm_smi:       RocmSMICommandConfig
    perf:           PerfCommandConfig
    ld_environment: dict

def load_command_config(config_path = "config/command_config.yaml"):
    if not os.path.exists(config_path):
        print(f"Warning: {config_path} not found. Utilizing baseline defaults.", file = sys.stderr)
        return CommandConfig(
            rocm_smi = RocmSMICommandConfig(
                base_command = ["rocm-smi", "--showuse", "--showmemuse", "--json"],
                device_flag  = "--device=",
                device_index = 0
            ),
            perf = PerfCommandConfig(
                base_command = ["perf", "stat", "-j", "-e"]
            ),
            ld_environment = {"LD_DEBUG": "statistics", "LD_BIND_NOW": "1"}
        )

    try:
        with open(config_path, "r") as f:
            raw_data = yaml.safe_load(f)
            
        if not raw_data:
            raw_data = {}    
        
        raw_data = raw_data.get("commands", {})

        gpu_data   = raw_data.get("rocm_smi", {})
        gpu_config = RocmSMICommandConfig(
            base_command = gpu_data.get("base_command", ["rocm-smi", "--showuse", "--showmemuse", "--json"]),
            device_flag  = gpu_data.get("device_flag", "--device="),
            device_index = gpu_data.get("device_index", 0)
        )
        
        cpu_data   = raw_data.get("perf", {})
        cpu_config = PerfCommandConfig(
            base_command = cpu_data.get("base_command", ["perf", "stat", "-j", "-e"])
        )
        
        ld_env = {}
        for k, v in raw_data.get("ld_environment", {}).items():
            ld_env[str(k)] = str(v)
            
        if not ld_env:
            ld_env = {"LD_DEBUG": "statistics", "LD_BIND_NOW": "1"}

        return CommandConfig(
            rocm_smi       = gpu_config,
            perf           = cpu_config,
            ld_environment = ld_env
        )

    except Exception as e:
        print(f"Warning: Error parsing {config_path} ({e}). Utilizing baseline defaults.", file=sys.stderr)
        return CommandConfig(
            rocm_smi = RocmSMICommandConfig(
                base_command = ["rocm-smi", "--showuse", "--showmemuse", "--json"],
                device_flag  = "--device=",
                device_index = 0
            ),
            perf = PerfCommandConfig(
                base_command = ["perf", "stat", "-j", "-e"]
            ),
            ld_environment = {"LD_DEBUG": "statistics", "LD_BIND_NOW": "1"}
        )