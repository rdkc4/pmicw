"""
Data Structures and Telemetry Schema Module.

This module defines the complete structural contract for the profiler's data layer,
handling environment state collection, metadata tracking, and target workload metrics.

Data Model Hierarchy Map:
    Measurement
    |-> Metadata
    |   |-> Version
    |   |-> SoftwareInfo
    |   |-> HardwareInfo
    |
    |-> Workload
    |
    |-> Metrics
        |-> WallTimeMetric
        |-> CPUMetric
        |-> GPUMetric
        |-> MemoryMetric
        |-> SystemMetric
"""

from dataclasses import dataclass
import datetime
import platform
import uuid
import psutil
import cpuinfo
import git
import amdsmi

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

class OSInfo:
    """
    Extracts underlying operating system data using `platform`
    """
    def __init__(self):
        self.name    = platform.system()
        self.version = platform.version()

    def __repr__(self):
        return f"OSInfo(name='{self.name}', version='{self.version}')"

class SoftwareInfo:
    def __init__(self):
        self.os = OSInfo()

    def __repr__(self):
        return f"SoftwareInfo(os={self.os})"

class CPUInfo:
    """
    Queries underlying host processor specifications using `cpuinfo` and `psutil`.
    Captures raw engineering brand strings, core topology layouts, and maximum clock caps.
    """
    def __init__(self):
        cpu_info            = cpuinfo.get_cpu_info()
        self.model          = cpu_info['brand_raw']
        self.architecture   = cpu_info['arch']
        self.physical_cores = psutil.cpu_count(logical=False)
        self.logical_cores  = psutil.cpu_count(logical=True)
        self.frequency      = psutil.cpu_freq().max

    def __repr__(self):
        return f"CPUInfo(model='{self.model}', architecture='{self.architecture}', physical_cores={self.physical_cores}, logical_cores={self.logical_cores}, frequency={self.frequency})"

class GPUInfo:
    """
    Probes host AMD graphics layout topology via the `amdsmi` driver wrapper library.
    Safely handles one-time runtime pointer bindings, capturing model contexts and total VRAM buffers.
    """
    def __init__(self):
        
        try:
            amdsmi.amdsmi_init()
            devices = amdsmi.amdsmi_get_processor_handles()

            if len(devices) > 0:
                info               = amdsmi.amdsmi_get_gpu_asic_info(devices[0])
                mem_info           = amdsmi.amdsmi_get_gpu_vram_usage(devices[0])
                self.model         = info.get('market_name', 'N/A')
                self.target        = info.get('target_graphics_version', 'N/A')
                self.vram_total_mb = mem_info.get('vram_total', 'N/A')
                self.vram_used_mb  = mem_info.get('vram_used', 'N/A')
            else:
                self.model         = "N/A"
                self.target        = "N/A"
                self.vram_total_mb = "N/A"
                self.vram_used_mb  = "N/A"

        except:
            self.model         = "N/A"
            self.target        = "N/A"
            self.vram_total_mb = "N/A"
            self.vram_used_mb  = "N/A"

        finally:
            try:
                amdsmi.amdsmi_shut_down()
            except:
                pass

    def __repr__(self):
        return f"GPUInfo(model='{self.model}', target='{self.target}', vram_total_mb='{self.vram_total_mb}', vram_used_mb='{self.vram_used_mb}')"

class MemoryInfo:
    """
    Extracts underlying memory data using `psutil`
    """
    def __init__(self):
        mem                = psutil.virtual_memory()
        swp                = psutil.swap_memory()
        self.total_mb      = mem.total     / (1024 ** 2)
        self.available_mb  = mem.available / (1024 ** 2)
        self.used_mb       = mem.used      / (1024 ** 2)
        self.free_mb       = mem.free      / (1024 ** 2)
        self.swap_total_mb = swp.total     / (1024 ** 2)
        self.swap_used_mb  = swp.used      / (1024 ** 2)
        self.swap_free_mb  = swp.free      / (1024 ** 2)

    def __repr__(self):
        return f"MemoryInfo(total_mb={self.total_mb}, available_mb={self.available_mb}, used_mb={self.used_mb}, free_mb={self.free_mb}, swap_total_mb={self.swap_total_mb}, swap_used_mb={self.swap_used_mb}, swap_free_mb={self.swap_free_mb})"

class HardwareInfo:
    def __init__(self):
        self.cpu    = CPUInfo()
        self.gpu    = GPUInfo()
        self.memory = MemoryInfo()

    def __repr__(self):
        return f"HardwareInfo(cpu={self.cpu}, gpu={self.gpu}, memory={self.memory})"

class Metadata:
    def __init__(self):
        self.run_id    = uuid.uuid4()
        self.timestamp = datetime.datetime.now().isoformat()
        self.version   = Version()
        self.software  = SoftwareInfo()
        self.hardware  = HardwareInfo()

    def __repr__(self):
        return f"Metadata(run_id='{self.run_id}', timestamp='{self.timestamp}', version={self.version}, software={self.software}, hardware={self.hardware})"

class Workload:
    """
    Configuration and iteration tracking
    """
    def __init__(self, name: str, arguments: list[str], iteration: int):
        self.name      = name
        self.arguments = arguments
        self.iteration = iteration

    def __repr__(self):
        return f"Workload(name='{self.name}', arguments={self.arguments}, iteration={self.iteration})"

@dataclass
class MetricStats:
    """Core statistical results calculated over multiple workload iteration samples."""
    mean_value:   float
    median_value: float
    stddev_value: float
    min_value:    float
    max_value:    float

@dataclass
class WallTimeMetric:
    """
    Tracks latency metrics. 
    total_ms represents the baseline accumulation across iterations.
    wall_time_stats unit: ms
    """
    total_ms:        float
    wall_time_stats: MetricStats

@dataclass
class IPCMetric:
    """
    Hardware instructions-per-cycle profiling parameters extracted via perf hardware counters.
    total_ipc represents the baseline accumulation across iterations.
    """
    total_instructions: int
    total_cycles:       int
    total_ipc:          float
    ipc_stats:          MetricStats

@dataclass
class TaskClockMetric:
    """
    CPU time consumed by the profiled task, measured via perf task-clock events.
    total_ms represents the accumulated task-clock time across all iterations.
    """
    total_ms:         float
    task_clock_stats: MetricStats

@dataclass
class L1CacheMetric:
    """
    Private L1 cache localization and data-miss trends.
    miss rate unit: %.
    """
    total_accesses:     int
    total_misses:       int
    total_miss_rate:    float
    l1_miss_rate_stats: MetricStats

@dataclass
class L2CacheMetric:
    """
    Private L2 cache localization and data-miss trends.
    miss rate unit: %
    """
    total_accesses:     int
    total_misses:       int
    total_miss_rate:    float
    l2_miss_rate_stats: MetricStats

@dataclass
class LLCacheMetric:
    """
    Last Level Cache (Shared LLC/L3 Cache) system performance footprints.
    miss rate unit: %
    """
    total_accesses:      int
    total_misses:        int
    total_miss_rate:     float
    llc_miss_rate_stats: MetricStats

@dataclass
class BranchPredictionMetric:
    """
    Tracks total conditional branches evaluated versus pipeline speculative mispredictions.
    """
    total_branches:          int
    total_branch_misses:     int
    total_branch_miss_rate:  float
    branch_miss_rate_stats:  MetricStats

@dataclass
class CPUMetric:
    """
    Unified execution core performance block.
    Aggregates compute intensity, pipeline hazards, and memory-subsystem cache hierarchies.
    """
    ipc:               IPCMetric
    task_clock:        TaskClockMetric
    l1_cache:          L1CacheMetric
    l2_cache:          L2CacheMetric
    llc_cache:         LLCacheMetric
    branch_prediction: BranchPredictionMetric

@dataclass
class GPUMetric:
    """
    Accelerated graphics compute block tracked via subprocess background loops using `rocm-smi`.
    Activity and VRAM units: %.
    """
    activity_stats: MetricStats
    vram_stats:     MetricStats

@dataclass
class MemoryMetric:
    """
    Host volatile workspace allocations sampled via psutil tracking threads.
    MEM and SWP units: %
    """
    mem_stats:  MetricStats
    swap_stats: MetricStats

@dataclass
class SystemMetric:
    """
    Linux kernel scheduler and software abstraction layer telemetry.
    Captures raw operational counts alongside structural thread behavior frequencies:
        - context_switches: CPU thread scheduling migrations.
        - page_faults: Virtual memory mapping re-allocations.
        - minor_faults: Quick memory mappings resolved without disk access.
        - major_faults: Heavy I/O blocking faults requiring physical disk page swaps.
    """
    total_context_switches: int
    total_page_faults:      int
    total_minor_faults:     int
    total_major_faults:     int
    context_switches_stats: MetricStats
    page_faults_stats:      MetricStats
    minor_faults_stats:     MetricStats
    major_faults_stats:     MetricStats

@dataclass
class Metrics:
    """The unified mathematical metric encompassing all active profiling vectors."""
    wall_time: WallTimeMetric
    cpu:       CPUMetric    | None
    gpu:       GPUMetric    | None
    memory:    MemoryMetric | None
    system:    SystemMetric | None

class Measurement:
    """
    The root node of the data schema layer.
    Combines environment configuration states, targeted workload loops, and fully computed 
    performance statistics into a single self-contained document ready for serialization.
    """
    def __init__(self, metadata: Metadata, workload: Workload, metrics: Metrics):
        self.metadata = metadata
        self.workload = workload
        self.metrics  = metrics
    
    def __repr__(self):
        return f"Measurement(metadata={self.metadata}, workload={self.workload}, metrics={self.metrics})"
