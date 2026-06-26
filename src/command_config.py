from dataclasses import dataclass, field, fields
import os
from pathlib import Path
import sys
import yaml

@dataclass
class RocmSMICommandConfig:
    base_command: list[str] = field(default_factory = lambda: ["rocm-smi", "--showuse", "--showmemuse", "--json"])
    device_flag:  str       = "--device="
    device_index: int       = 0

@dataclass
class PerfCommandConfig:
    base_command: list[str] = field(default_factory = lambda: ["perf", "stat", "-j", "-e"])

@dataclass
class BashCommandWrapperConfig:
    base_command: list[str] = field(default_factory = lambda: ["sh", "-c", 'kill -STOP $$; exec "$@"', "--"])

@dataclass
class BPFTraceStartupCommandConfig:
    # bpftrace requires sudo => add your user as passwordless sudoer for bpftrace
    base_command: list[str] = field(default_factory = lambda: ["sudo", "bpftrace", "-q"])
    pid_flag:     str       = "-p"
    script:       str       = "scripts/linker_prof.bt"

@dataclass
class BPFTraceTSACommandConfig:
    base_command: list[str] = field(default_factory = lambda: ["sudo", "bpftrace", "-q"])
    pid_flag:     str       = "-p"
    script:       str       = "scripts/thread_prof.bt"

@dataclass
class CommandConfig:
    rocm_smi:         RocmSMICommandConfig         = field(default_factory = RocmSMICommandConfig)
    perf:             PerfCommandConfig            = field(default_factory = PerfCommandConfig)
    bash_wrapper:     BashCommandWrapperConfig     = field(default_factory = BashCommandWrapperConfig)
    bpftrace_startup: BPFTraceStartupCommandConfig = field(default_factory = BPFTraceStartupCommandConfig)
    bpftrace_tsa:     BPFTraceTSACommandConfig     = field(default_factory = BPFTraceTSACommandConfig)

def load_command_config(config_path: Path | str):
    if not os.path.exists(config_path):
        print(f"Warning: {config_path} not found. Utilizing baseline defaults.", file = sys.stderr)
        return CommandConfig()

    try:
        with open(config_path, "r") as f:
            raw_data = yaml.safe_load(f) or {}
            
        commands = raw_data.get("commands", {})

        return CommandConfig(
            rocm_smi         = from_dict_safe(RocmSMICommandConfig,         commands.get("rocm_smi")),
            perf             = from_dict_safe(PerfCommandConfig,            commands.get("perf")),
            bash_wrapper     = from_dict_safe(BashCommandWrapperConfig,     commands.get("bash_command_wrapper")),
            bpftrace_startup = from_dict_safe(BPFTraceStartupCommandConfig, commands.get("bpftrace_startup"))
        )

    except Exception as e:
        print(f"Warning: Error parsing {config_path} ({e}). Utilizing baseline defaults.", file = sys.stderr)
        return CommandConfig()
    
def from_dict_safe(cls, data: dict):
    """Instantiates a dataclass, ignoring any unexpected keys in the dictionary."""
    if not isinstance(data, dict):
        return cls()

    valid_fields  = {f.name for f in fields(cls)}
    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
    
    return cls(**filtered_data)