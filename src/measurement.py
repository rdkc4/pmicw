"""
Data Structures and Telemetry Schema Module.

This module defines the complete structural contract for the profiler's data layer,
handling environment state collection, metadata tracking, and target workload metrics.

Data Model Hierarchy Map:
    Measurement
    |-> Metadata
    |   |-> Version
    |   |   |-> Git Repository URL
    |   |   |-> Active Branch Name
    |   |   |-> Current Commit Hash
    |   |
    |   |-> SoftwareInfo
    |   |   |-> OSInfo
    |   |   |   |-> OS Name
    |   |   |   |-> OS Version
    |   |
    |   |-> HardwareInfo
    |   |   |-> CPUInfo
    |   |   |   |-> Model Name
    |   |   |   |-> Architecture
    |   |   |   |-> Physical Cores
    |   |   |   |-> Logical Cores
    |   |   |   |-> Max Frequency
    |
    |-> Workload
    |   |-> Name
    |   |-> Iterations
    |   |-> Warmup Iterations
    |   |-> Arguments
    |
    |-> Metrics
    |   |-> WallTimeMetric
    |   |   |-> total_ms
    |   |   |-> wall_time_stats_ms (mean, median, stddev, min, max)
    |   |   
    |   |-> CPUMetric
    |   |   |-> IPCMetric
    |   |   |   |-> total_instructions
    |   |   |   |-> total_cycles
    |   |   |   |-> ipc_stats (mean, median, stddev, min, max)
    |   |   |
    |   |   |-> TaskClockMetric
    |   |   |   |-> total_ms
    |   |   |   |-> task_clock_stats_ms (mean, median, stddev, min, max)
    |   |   |   
    |   |   |-> L1CacheMetric
    |   |   |   |-> totald_accesses
    |   |   |   |-> totald_misses
    |   |   |   |-> totali_accesses
    |   |   |   |-> totali_misses
    |   |   |   |-> l1d_miss_rate_stats_pct (mean, median, stddev, min, max)
    |   |   |   |-> l1i_miss_rate_stats_pct (mean, median, stddev, min, max)
    |   |   |
    |   |   |-> L2CacheMetric
    |   |   |   |-> total_accesses
    |   |   |   |-> total_misses
    |   |   |   |-> l2_miss_rate_stats_pct (mean, median, stddev, min, max)
    |   |   |
    |   |   |-> LLCacheMetric
    |   |   |   |-> total_accesses
    |   |   |   |-> total_misses
    |   |   |   |-> llc_miss_rate_stats_pct (mean, median, stddev, min, max)
    |   |   |
    |   |   |-> BranchPredictionMetric
    |   |   |   |-> total_branches
    |   |   |   |-> total_branch_misses
    |   |   |   |-> branch_miss_rate_stats_pct (mean, median, stddev, min, max)
    |   |
    |   |-> GPUMetric
    |   |   |-> activity_stats_pct (mean, median, stddev, min, max)
    |   |   |-> vram_stats_pct (mean, median, stddev, min, max)
    |   |
    |   |-> MemoryMetric
    |   |   |-> rss_stats_mb (mean, median, stddev, min, max)
    |   |   |-> vms_stats_mb (mean, median, stddev, min, max)
    |   |
    |   |-> SystemMetric
    |   |   |-> total_context_switches
    |   |   |-> total_page_faults
    |   |   |-> total_minor_faults
    |   |   |-> total_major_faults
    |   |   |-> context_switches_stats (mean, median, stddev, min, max)
    |   |   |-> page_faults_stats (mean, median, stddev, min, max)
    |   |   |-> minor_faults_stats (mean, median, stddev, min, max)
    |   |   |-> major_faults_stats (mean, median, stddev, min, max)
    |   |
    |   |-> StartupMetric
    |   |   |-> total_cycles
    |   |   |-> total_link_cycles
    |   |   |-> startup_time_stats_ms (mean, median, stddev, min, max)
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
    
    def to_csv_header(self) -> str:
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
    
    def to_csv_header(self) -> str:
        return "os_name,os_version"
    
    def data_to_csv(self) -> str:
        return f"{self.name},{self.version}"

class SoftwareInfo:
    def __init__(self):
        self.os = OSInfo()

    def __repr__(self):
        return f"SoftwareInfo(os={self.os})"
    
    def to_csv_header(self) -> str:
        return self.os.to_csv_header()
    
    def data_to_csv(self) -> str:
        return self.os.data_to_csv()

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

    def to_csv_header(self) -> str:
        return "cpu_model,cpu_architecture,physical_cores,logical_cores,cpu_frequency"

    def data_to_csv(self) -> str:
        return f"{self.model},{self.architecture},{self.physical_cores},{self.logical_cores},{self.frequency}"

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

    def to_csv_header(self) -> str:
        return "gpu_model,gpu_target,vram_total_mb,vram_used_mb"

    def data_to_csv(self) -> str:
        return f"{self.model},{self.target},{self.vram_total_mb},{self.vram_used_mb}"

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

    def to_csv_header(self) -> str:
        return "total_mb,available_mb,used_mb,free_mb,swap_total_mb,swap_used_mb,swap_free_mb"

    def data_to_csv(self) -> str:
        return f"{self.total_mb},{self.available_mb},{self.used_mb},{self.free_mb},{self.swap_total_mb},{self.swap_used_mb},{self.swap_free_mb}"

class HardwareInfo:
    def __init__(self):
        self.cpu    = CPUInfo()
        self.gpu    = GPUInfo()
        self.memory = MemoryInfo()

    def __repr__(self):
        return f"HardwareInfo(cpu={self.cpu}, gpu={self.gpu}, memory={self.memory})"
    
    def to_csv_header(self) -> str:
        return f"{self.cpu.to_csv_header()},{self.gpu.to_csv_header()},{self.memory.to_csv_header()}"
    
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

    def to_csv_header(self) -> str:
        return f"run_id,timestamp,{self.version.to_csv_header()},{self.software.to_csv_header()},{self.hardware.to_csv_header()}"
    
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

    def to_csv_header(self) -> str:
        return "workload_name,iterations,warmup_iterations,arguments"
    
    def data_to_csv(self) -> str:
        args_str = " ".join(self.arguments)
        return f"{self.name},{self.iterations},{self.warmup_iterations},\"{args_str}\""

@dataclass
class MetricStats:
    """Core statistical results calculated over multiple workload iteration samples."""
    mean_value:   float
    median_value: float
    stddev_value: float
    min_value:    float
    max_value:    float

    def to_csv_header(self, prefix: str) -> str:
        return f"{prefix}_mean,{prefix}_median,{prefix}_stddev,{prefix}_min,{prefix}_max"

    def data_to_csv(self) -> str:
        return f"{self.mean_value},{self.median_value},{self.stddev_value},{self.min_value},{self.max_value}"

@dataclass
class WallTimeMetric:
    """
    Tracks latency metrics. 
    total_ms represents the baseline accumulation across iterations.
    wall_time_stats unit: ms
    """
    total_ms:           float
    wall_time_stats_ms: MetricStats

    def to_csv_header(self) -> str:
        return f"wall_time_total_ms,{self.wall_time_stats_ms.to_csv_header("wall_time")}"
    
    def data_to_csv(self) -> str:
        return f"{self.total_ms},{self.wall_time_stats_ms.data_to_csv()}"

@dataclass
class IPCMetric:
    """
    Hardware instructions-per-cycle profiling parameters extracted via perf hardware counters.
    total_ipc represents the baseline accumulation across iterations.
    """
    total_instructions: int
    total_cycles:       int
    ipc_stats:          MetricStats

    def to_csv_header(self) -> str:
        return f"total_instructions,total_cycles,{self.ipc_stats.to_csv_header("ipc")}"
    
    def data_to_csv(self) -> str:
        return f"{self.total_instructions},{self.total_cycles},{self.ipc_stats.data_to_csv()}"

@dataclass
class TaskClockMetric:
    """
    CPU time consumed by the profiled task, measured via perf task-clock events.
    total_ms represents the accumulated task-clock time across all iterations.
    """
    total_ms:            float
    task_clock_stats_ms: MetricStats

    def to_csv_header(self) -> str:
        return f"task_clock_total_ms,{self.task_clock_stats_ms.to_csv_header("task_clock")}"

    def data_to_csv(self) -> str:
        return f"{self.total_ms},{self.task_clock_stats_ms.data_to_csv()}"

@dataclass
class L1CacheMetric:
    """
    Private L1 cache localization and data-miss trends.
    miss rate unit: %.
    """
    totald_accesses:         int
    totald_misses:           int
    totali_accesses:         int
    totali_misses:           int
    l1d_miss_rate_stats_pct: MetricStats
    l1i_miss_rate_stats_pct: MetricStats

    def to_csv_header(self) -> str:
        return f"l1_totald_accesses,l1_totald_misses,l1_totali_accesses,l1_totali_misses,{self.l1d_miss_rate_stats_pct.to_csv_header('l1d_miss_rate')},{self.l1i_miss_rate_stats_pct.to_csv_header('l1i_miss_rate')}"

    def data_to_csv(self) -> str:
        return f"{self.totald_accesses},{self.totald_misses},{self.totali_accesses},{self.totali_misses},{self.l1d_miss_rate_stats_pct.data_to_csv()},{self.l1i_miss_rate_stats_pct.data_to_csv()}"

@dataclass
class L2CacheMetric:
    """
    Private L2 cache localization and data-miss trends.
    miss rate unit: %
    """
    total_accesses:         int
    total_misses:           int
    l2_miss_rate_stats_pct: MetricStats

    def to_csv_header(self) -> str:
        return f"l2_total_accesses,l2_total_misses,{self.l2_miss_rate_stats_pct.to_csv_header('l2_miss_rate')}"

    def data_to_csv(self) -> str:
        return f"{self.total_accesses},{self.total_misses},{self.l2_miss_rate_stats_pct.data_to_csv()}"

@dataclass
class LLCacheMetric:
    """
    Last Level Cache (Shared LLC/L3 Cache) system performance footprints.
    miss rate unit: %
    """
    total_accesses:          int
    total_misses:            int
    llc_miss_rate_stats_pct: MetricStats

    def to_csv_header(self) -> str:
        return f"llc_total_accesses,llc_total_misses,{self.llc_miss_rate_stats_pct.to_csv_header('llc_miss_rate')}"

    def data_to_csv(self) -> str:
        return f"{self.total_accesses},{self.total_misses},{self.llc_miss_rate_stats_pct.data_to_csv()}"

@dataclass
class BranchPredictionMetric:
    """
    Tracks total conditional branches evaluated versus pipeline speculative mispredictions.
    """
    total_branches:             int
    total_branch_misses:        int
    branch_miss_rate_stats_pct: MetricStats

    def to_csv_header(self) -> str:
        return f"total_branches,total_branch_misses,{self.branch_miss_rate_stats_pct.to_csv_header('branch_miss_rate')}"

    def data_to_csv(self) -> str:
        return f"{self.total_branches},{self.total_branch_misses},{self.branch_miss_rate_stats_pct.data_to_csv()}"

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

    def to_csv_header(self) -> str:
        return f"{self.ipc.to_csv_header()},{self.task_clock.to_csv_header()},{self.l1_cache.to_csv_header()},{self.l2_cache.to_csv_header()},{self.llc_cache.to_csv_header()},{self.branch_prediction.to_csv_header()}"

    def data_to_csv(self) -> str:
        return f"{self.ipc.data_to_csv()},{self.task_clock.data_to_csv()},{self.l1_cache.data_to_csv()},{self.l2_cache.data_to_csv()},{self.llc_cache.data_to_csv()},{self.branch_prediction.data_to_csv()}"

@dataclass
class GPUMetric:
    """
    Accelerated graphics compute block tracked via subprocess background loops using `rocm-smi`.
    Activity and VRAM units: %.
    """
    activity_stats_pct: MetricStats
    vram_stats_pct:     MetricStats

    def to_csv_header(self) -> str:
        return f"{self.activity_stats_pct.to_csv_header('gpu_activity_pct')},{self.vram_stats_pct.to_csv_header('gpu_vram_pct')}"

    def data_to_csv(self) -> str:
        return f"{self.activity_stats_pct.data_to_csv()},{self.vram_stats_pct.data_to_csv()}"

@dataclass
class MemoryMetric:
    """
    Host volatile workspace allocations sampled via psutil tracking threads.
    rss and vms units: mb
    """
    rss_stats_mb: MetricStats
    vms_stats_mb: MetricStats

    def to_csv_header(self) -> str:
        return f"{self.rss_stats_mb.to_csv_header('rss_mb')},{self.vms_stats_mb.to_csv_header('vms_mb')}"

    def data_to_csv(self) -> str:
        return f"{self.rss_stats_mb.data_to_csv()},{self.vms_stats_mb.data_to_csv()}"

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

    def to_csv_header(self) -> str:
        return f"total_context_switches,total_page_faults,total_minor_faults,total_major_faults,{self.context_switches_stats.to_csv_header('context_switches')},{self.page_faults_stats.to_csv_header('page_faults')},{self.minor_faults_stats.to_csv_header('minor_faults')},{self.major_faults_stats.to_csv_header('major_faults')}"

    def data_to_csv(self) -> str:
        return f"{self.total_context_switches},{self.total_page_faults},{self.total_minor_faults},{self.total_major_faults},{self.context_switches_stats.data_to_csv()},{self.page_faults_stats.data_to_csv()},{self.minor_faults_stats.data_to_csv()},{self.major_faults_stats.data_to_csv()}"

@dataclass
class StartupMetric:
    """
    Measures dynamic linker (ld.so) startup overhead captured via LD_DEBUG=statistics.
    Startup time stats represent mean, median, stddev, min, max startup time
    startup_time_stats unit: ms
    """
    total_cycles:          int
    total_link_cycles:     int
    startup_time_stats_ms: MetricStats

    def to_csv_header(self) -> str:
        return f"startup_total_cycles,startup_total_link_cycles,{self.startup_time_stats_ms.to_csv_header('startup_time_ms')}"

    def data_to_csv(self) -> str:
        return f"{self.total_cycles},{self.total_link_cycles},{self.startup_time_stats_ms.data_to_csv()}"

@dataclass
class Metrics:
    """The unified mathematical metric encompassing all active profiling vectors."""
    wall_time: WallTimeMetric
    cpu:       CPUMetric     | None
    gpu:       GPUMetric     | None
    memory:    MemoryMetric  | None
    system:    SystemMetric  | None
    startup:   StartupMetric | None

    def to_csv_header(self) -> str:
        headers = [self.wall_time.to_csv_header()]
        if self.cpu:     headers.append(self.cpu.to_csv_header())
        if self.gpu:     headers.append(self.gpu.to_csv_header())
        if self.memory:  headers.append(self.memory.to_csv_header())
        if self.system:  headers.append(self.system.to_csv_header())
        if self.startup: headers.append(self.startup.to_csv_header())
        return ",".join(headers)

    def data_to_csv(self) -> str:
        data = [self.wall_time.data_to_csv()]
        if self.cpu:     data.append(self.cpu.data_to_csv())
        if self.gpu:     data.append(self.gpu.data_to_csv())
        if self.memory:  data.append(self.memory.data_to_csv())
        if self.system:  data.append(self.system.data_to_csv())
        if self.startup: data.append(self.startup.data_to_csv())
        return ",".join(data)

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

    def to_csv_header(self) -> str:
        return f"{self.metadata.to_csv_header()},{self.workload.to_csv_header()},{self.metrics.to_csv_header()}"

    def to_csv(self, show_header: bool) -> str:
        data = f"{self.metadata.data_to_csv()},{self.workload.data_to_csv()},{self.metrics.data_to_csv()}"
        
        if show_header:
            return f"{self.to_csv_header()}\n{data}"
        
        return data
