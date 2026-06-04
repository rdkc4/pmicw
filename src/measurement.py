"""
Data Structures and Telemetry Schema Module

This module defines the structural contract for the profiler's data layer,
handling environment state collection, metadata tracking, workload configuration,
and target workload metrics.

Key Components:

1. Version
   - Captures Git repository context: repository URL, branch, commit hash.
   - Falls back gracefully to "N/A" if not in a Git repository.

2. OSInfo & SoftwareInfo
   - OSInfo: Provides operating system name and version via `platform`.
   - SoftwareInfo: Aggregates OSInfo.

3. CPUInfo, GPUInfo, MemoryInfo
   - CPUInfo: Captures CPU model, architecture, physical/logical cores, max frequency.
   - GPUInfo: Probes AMD GPUs via `amdsmi` for model, target architecture, VRAM.
   - MemoryInfo: Captures total, available, used, free RAM and swap memory in MB.

4. HardwareInfo
   - Aggregates CPUInfo, GPUInfo, and MemoryInfo.

5. Metadata
   - Tracks run_id (UUID), timestamp, Version, SoftwareInfo, HardwareInfo.

6. Workload
   - Tracks workload name, iterations, warmup iterations, and arguments.

7. Metrics
   - Wraps segment-specific metrics in a Record and supports CSV serialization.

8. Measurement
   - Combines Metadata, Workload, and Metrics for a full experiment snapshot.
   - CSV output leverages ProfilerConfig to determine column order and segment fields.

CSV Schema Overview:

- Static columns: Metadata + Workload
- Dynamic columns: Metrics per segment as defined in ProfilerConfig
- Column order is strictly controlled by Measurement.to_csv_header() and Measurement.data_to_csv()
- Metrics serialization:
    - Metrics.data_to_csv(expected_fields) ensures alignment with CSV schema
    - Empty fields are inserted if a metric segment is missing

CSV Generation Example:

header = measurement.to_csv_header()
row    = measurement.data_to_csv()

Notes:

- The profiler supports dynamic segment configuration; the Measurement class
  queries ProfilerConfig for the expected CSV fields, ensuring forward compatibility.
- Reordering calls to to_csv_header() or data_to_csv() may break existing CSV datasets.
- Metrics are flattened per segment; missing or unavailable fields result in empty CSV columns.
"""

from dataclasses import dataclass
import datetime
import platform
import uuid
import psutil
import cpuinfo
import git

from metrics_config import ProfilerConfig
from record_types import Record

class Version:
    """
    Extracts underlying Git repository configurations using `GitPython`.
    Falls back gracefully to "N/A" strings if the execution context is not a valid Git tree.
    """
    def __init__(self):
        try:
            repo = git.Repo(search_parent_directories=True)
            self.repository = repo.remotes.origin.url
            self.branch     = repo.active_branch.name
            self.commit     = repo.head.commit.hexsha
        except:
            self.repository = "N/A"
            self.branch     = "N/A"
            self.commit     = "N/A"
    
    def __repr__(self):
        return f"Version(repository='{self.repository}', branch='{self.branch}', commit='{self.commit}')"
    
    @classmethod
    def to_csv_header(cls) -> str:
        return "repository,branch,commit"

    def data_to_csv(self) -> str:
        return f"{self.repository},{self.branch},{self.commit}"

class OSInfo:
    """
    Extracts underlying operating system data using `platform`
    """
    def __init__(self):
        self.name    = platform.system()
        self.version = platform.version()

    def __repr__(self):
        return f"OSInfo(name='{self.name}', version='{self.version}')"
    
    @classmethod
    def to_csv_header(cls) -> str:
        return "os_name,os_version"
    
    def data_to_csv(self) -> str:
        return f"{self.name},{self.version}"

class SoftwareInfo:
    def __init__(self):
        self.os = OSInfo()

    def __repr__(self):
        return f"SoftwareInfo(os={self.os})"
    
    @classmethod
    def to_csv_header(cls) -> str:
        return OSInfo.to_csv_header()
    
    def data_to_csv(self) -> str:
        return self.os.data_to_csv()

class CPUInfo:
    """
    Queries underlying host processor specifications using `cpuinfo` and `psutil`.
    Captures raw engineering brand strings, core topology layouts, and maximum clock caps.
    """
    def __init__(self):
        cpu_info            = cpuinfo.get_cpu_info()
        self.model          = cpu_info.get('brand_raw', 'N/A').replace(',', ' ')
        self.architecture   = cpu_info.get('arch', 'N/A')
        self.physical_cores = psutil.cpu_count(logical=False)
        self.logical_cores  = psutil.cpu_count(logical=True)
        self.frequency      = psutil.cpu_freq().max

    def __repr__(self):
        return f"CPUInfo(model='{self.model}', architecture='{self.architecture}', physical_cores={self.physical_cores}, logical_cores={self.logical_cores}, frequency={self.frequency})"

    @classmethod
    def to_csv_header(cls) -> str:
        return "cpu_model,cpu_architecture,cpu_physical_cores,cpu_logical_cores,cpu_frequency"

    def data_to_csv(self) -> str:
        return f"{self.model},{self.architecture},{self.physical_cores},{self.logical_cores},{self.frequency}"

class GPUInfo:
    """
    Probes host AMD graphics layout topology via the `amdsmi` driver wrapper library.
    Safely handles one-time runtime pointer bindings, capturing model contexts and total VRAM buffers.
    """
    def __init__(self):
        
        try:
            import amdsmi
            amdsmi.amdsmi_init()
            devices = amdsmi.amdsmi_get_processor_handles()

            if len(devices) > 0:
                info               = amdsmi.amdsmi_get_gpu_asic_info(devices[0])
                mem_info           = amdsmi.amdsmi_get_gpu_vram_usage(devices[0])
                self.model         = info.get('market_name', 'N/A').replace(',', ' ')
                self.target        = info.get('target_graphics_version', 'N/A')
                self.vram_total_mb = float(mem_info.get('vram_total', 0.0))
                self.vram_used_mb  = float(mem_info.get('vram_used', 0.0))
            else:
                self.model         = "N/A"
                self.target        = "N/A"
                self.vram_total_mb = 0.0
                self.vram_used_mb  = 0.0

        except:
            self.model         = "N/A"
            self.target        = "N/A"
            self.vram_total_mb = 0.0
            self.vram_used_mb  = 0.0

        finally:
            try:
                amdsmi.amdsmi_shut_down()
            except:
                pass

    def __repr__(self):
        return f"GPUInfo(model='{self.model}', target='{self.target}', vram_total_mb='{self.vram_total_mb}', vram_used_mb='{self.vram_used_mb}')"

    @classmethod
    def to_csv_header(cls) -> str:
        return "gpu_model,gpu_target,gpu_vram_total_mb,gpu_vram_used_mb"

    def data_to_csv(self) -> str:
        return f"{self.model},{self.target},{self.vram_total_mb},{self.vram_used_mb}"

class MemoryInfo:
    """
    Extracts underlying memory data using `psutil`
    """
    def __init__(self):
        mem                   = psutil.virtual_memory()
        swp                   = psutil.swap_memory()
        self.mem_total_mb     = mem.total     / (1024 ** 2)
        self.mem_available_mb = mem.available / (1024 ** 2)
        self.mem_used_mb      = mem.used      / (1024 ** 2)
        self.mem_free_mb      = mem.free      / (1024 ** 2)
        self.swp_total_mb     = swp.total     / (1024 ** 2)
        self.swp_used_mb      = swp.used      / (1024 ** 2)
        self.swp_free_mb      = swp.free      / (1024 ** 2)

    def __repr__(self):
        return f"MemoryInfo(total_mb={self.mem_total_mb}, available_mb={self.mem_available_mb}, used_mb={self.mem_used_mb}, free_mb={self.mem_free_mb}, swap_total_mb={self.swp_total_mb}, swap_used_mb={self.swp_used_mb}, swap_free_mb={self.swp_free_mb})"

    @classmethod
    def to_csv_header(cls) -> str:
        return "mem_total_mb,mem_available_mb,mem_used_mb,mem_free_mb,swp_total_mb,swp_used_mb,swp_free_mb"

    def data_to_csv(self) -> str:
        return f"{self.mem_total_mb},{self.mem_available_mb},{self.mem_used_mb},{self.mem_free_mb},{self.swp_total_mb},{self.swp_used_mb},{self.swp_free_mb}"

class HardwareInfo:
    def __init__(self):
        self.cpu    = CPUInfo()
        self.gpu    = GPUInfo()
        self.memory = MemoryInfo()

    def __repr__(self):
        return f"HardwareInfo(cpu={self.cpu}, gpu={self.gpu}, memory={self.memory})"
    
    @classmethod
    def to_csv_header(cls) -> str:
        return f"{CPUInfo.to_csv_header()},{GPUInfo.to_csv_header()},{MemoryInfo.to_csv_header()}"
    
    def data_to_csv(self) -> str:
        return f"{self.cpu.data_to_csv()},{self.gpu.data_to_csv()},{self.memory.data_to_csv()}"

class Metadata:
    def __init__(self):
        self.run_id    = uuid.uuid4()
        self.timestamp = datetime.datetime.now().isoformat()
        self.version   = Version()
        self.software  = SoftwareInfo()
        self.hardware  = HardwareInfo()

    def __repr__(self):
        return f"Metadata(run_id='{self.run_id}', timestamp='{self.timestamp}', version={self.version}, software={self.software}, hardware={self.hardware})"

    @classmethod
    def to_csv_header(cls) -> str:
        return f"run_id,timestamp,{Version.to_csv_header()},{SoftwareInfo.to_csv_header()},{HardwareInfo.to_csv_header()}"
    
    def data_to_csv(self) -> str:
        return f"{self.run_id},{self.timestamp},{self.version.data_to_csv()},{self.software.data_to_csv()},{self.hardware.data_to_csv()}"

@dataclass
class Workload:
    """
    Configuration and iteration tracking
    """
    name:              str 
    iterations:        int
    warmup_iterations: int
    arguments:         list[str] 

    @classmethod
    def to_csv_header(cls) -> str:
        return "workload_name,workload_iterations,workload_warmup_iterations,workload_arguments"
    
    def data_to_csv(self) -> str:
        args_str = " ".join(self.arguments or [])
        return f"{self.name},{self.iterations},{self.warmup_iterations},\"{args_str}\""
    
@dataclass
class Metrics:
    record: Record

    def data_to_csv(self, expected_fields: list[str]) -> str:
        return ",".join(str(self.record[field]) if field in self.record else "" for field in expected_fields)
    
class Measurement:
    def __init__(self, metadata: Metadata, workload: Workload, metrics: dict[str, Metrics], cfg: ProfilerConfig):
        self.metadata = metadata
        self.workload = workload
        self.metrics  = metrics
        self.cfg      = cfg

    def __repr__(self):
        return (
            f"Measurement(metadata={self.metadata}, workload={self.workload}, "
            f"results={list(self.metrics)})"
        )

    def to_csv_header(self) -> str:
        return f"{Metadata.to_csv_header()},{Workload.to_csv_header()},{','.join(self.cfg.csv_fields())}"

    def data_to_csv(self) -> str:
        static_cols = f"{self.metadata.data_to_csv()},{self.workload.data_to_csv()}"

        dynamic_parts: list[str] = []
        for seg_name, seg_cfg in self.cfg.segments.items():
            expected = seg_cfg.output_fields()
            result   = self.metrics.get(seg_name)
            if result:
                dynamic_parts.append(result.data_to_csv(expected))

            else:
                dynamic_parts.append(",".join([""] * len(expected)))

        return f"{static_cols},{','.join(dynamic_parts)}"