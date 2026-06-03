"""
Data Structures and Telemetry Schema Module.

This module defines the complete structural contract for the profiler's data layer,
handling environment state collection, metadata tracking, and target workload metrics.

Data Model Hierarchy Map:
    Measurement
    |-> Metadata
    |   |-> Run ID
    |   |-> Timestamp
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
    |   |   |
    |   |   |-> GPUInfo
    |   |   |   |-> Model Name
    |   |   |   |-> Target Architecture
    |   |   |   |-> Total VRAM
    |   |   |   |-> Used VRAM
    |   |   |
    |   |   |-> MemoryInfo
    |   |   |   |-> Total MEM
    |   |   |   |-> Available MEM
    |   |   |   |-> Used MEM
    |   |   |   |-> Free MEM
    |   |   |   |-> Total SWP
    |   |   |   |-> Used SWP
    |   |   |   |-> Free SWP
    |
    |-> Workload
    |   |-> Name
    |   |-> Iterations
    |   |-> Warmup Iterations
    |   |-> Arguments
    |
    |-> Metrics
    |   |-> WallTimeMetric
    |   |   |-> wall_time_total_ms
    |   |   |-> wall_time_stats_ms (mean, median, stddev, min, max)
    |   |   
    |   |-> CPUMetric
    |   |   |-> IPCMetric
    |   |   |   |-> total_instructions
    |   |   |   |-> total_cycles
    |   |   |   |-> ipc_stats (mean, median, stddev, min, max)
    |   |   |
    |   |   |-> TaskClockMetric
    |   |   |   |-> task_clock_total_ms
    |   |   |   |-> task_clock_stats_ms (mean, median, stddev, min, max)
    |   |   |   
    |   |   |-> L1CacheMetric
    |   |   |   |-> l1d_total_accesses
    |   |   |   |-> l1d_total_misses
    |   |   |   |-> l1i_total_accesses
    |   |   |   |-> l1i_total_misses
    |   |   |   |-> l1d_miss_rate_stats_pct (mean, median, stddev, min, max)
    |   |   |   |-> l1i_miss_rate_stats_pct (mean, median, stddev, min, max)
    |   |   |
    |   |   |-> L2CacheMetric
    |   |   |   |-> l2_total_accesses
    |   |   |   |-> l2_total_misses
    |   |   |   |-> l2_miss_rate_stats_pct (mean, median, stddev, min, max)
    |   |   |
    |   |   |-> LLCacheMetric
    |   |   |   |-> llc_total_accesses
    |   |   |   |-> llc_total_misses
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
    |   |   |-> total_page_faults
    |   |   |-> total_minor_faults
    |   |   |-> total_major_faults
    |   |   |-> rss_stats_mb (mean, median, stddev, min, max)
    |   |   |-> vms_stats_mb (mean, median, stddev, min, max)
    |   |   |-> page_faults_stats (mean, median, stddev, min, max)
    |   |   |-> minor_faults_stats (mean, median, stddev, min, max)
    |   |   |-> major_faults_stats (mean, median, stddev, min, max)
    |   |
    |   |-> StartupMetric
    |   |   |-> total_link_cycles
    |   |   |-> startup_time_stats_ms (mean, median, stddev, min, max)
    |   |
    |   |-> ThreadMetric
    |   |   |-> total_context_switches
    |   |   |-> context_switches_stats (mean, median, stddev, min, max)
    |   |   |-> thread_count_stats (mean, median, stddev, min, max)
    |   |   |-> thread_utilization_stats (mean, median, stddev, min, max)


CSV Schema Overview

Columns are flattened and ordered as:
 - Metadata (run_id, timestamp)
 - Version (repository, branch, commit)
 - OS info (os_name, os_version)
 - CPU info (cpu_model, cpu_architecture, cpu_physical_cores, cpu_logical_cores, cpu_frequency)
 - GPU info (gpu_model, gpu_target, gpu_vram_total_mb, gpu_vram_used_mb)
 - Memory info (mem_total_mb, mem_available_mb, mem_used_mb, mem_free_mb, swp_total_mb, swp_used_mb, swp_free_mb)
 - Workload (workload_name, workload_iterations, workload_warmup_iterations, workload_arguments); 
            workload arguments are wrapped in quotes and separated by space: "arg1 arg2"
 - WallTime metric (wall_time_total_ms, wall_time_ms_(stats))
 - IPC metric (total_instructions, total_cycles, ipc_(stats))
 - TaskClock metric (task_clock_total_ms, task_clock_ms_(stats))
 - L1C metric (l1d_total_accesses, l1d_total_misses, l1i_total_accesses, l1i_total_misses, 
               l1d_miss_rate_pct_(stats), l1i_miss_rate_pct_(stats))
 - L2C metric (l2_total_accesses, l2_total_misses, l2_miss_rate_pct_(stats))
 - LLC metric (llc_total_accesses, llc_total_misses, llc_miss_rate_pct_(stats))
 - Branch metric (total_branches, total_branch_misses, branch_miss_rate_pct_(stats))
 - GPU metric (gpu_activity_pct_(stats), gpu_vram_pct_(stats))
 - Memory metric (rss_mb_(stats), vms_mb_(stats))
 - System metric (total_page_faults, total_minor_faults, total_major_faults, 
                  page_faults_(stats), minor_faults_(stats), major_faults_(stats))
 - Startup metric (linker_total_cycles, startup_time_ms_(stats))
 - Thread metric (total_context_switches, context_switches_(stats), thread_count_(stats), thread_utilization_(stats))
 - Note: (stats) has values: {mean, median, stddev, min, max}
 
Column/Row generation:
 - Columns are generated using Measurement.to_csv_header()
 - Rows are generated using Measurement.data_to_csv()
 - Warning: reordering of to_csv_header() and data_to_csv() calls can break existing csv datasets
"""

from dataclasses import dataclass
import datetime
import platform
import uuid
import psutil
import cpuinfo
import git

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
class MetricStats:
    """Core statistical results calculated over multiple workload iteration samples."""
    mean_value:   float
    median_value: float
    stddev_value: float
    min_value:    float
    max_value:    float

    @classmethod
    def to_csv_header(cls, prefix: str) -> str:
        return f"{prefix}_mean,{prefix}_median,{prefix}_stddev,{prefix}_min,{prefix}_max"

    def data_to_csv(self) -> str:
        return f"{self.mean_value},{self.median_value},{self.stddev_value},{self.min_value},{self.max_value}"

@dataclass
class WallTimeMetric:
    """
    Tracks latency metrics. 
    wall_time_total_ms represents the baseline accumulation across iterations.
    """
    wall_time_total_ms: float
    wall_time_stats_ms: MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"wall_time_total_ms,{MetricStats.to_csv_header('wall_time_ms')}"
    
    def data_to_csv(self) -> str:
        return f"{self.wall_time_total_ms},{self.wall_time_stats_ms.data_to_csv()}"

@dataclass
class IPCMetric:
    """
    Hardware instructions-per-cycle profiling parameters extracted via perf hardware counters.
    total_ipc represents the baseline accumulation across iterations.
    """
    total_instructions: int
    total_cycles:       int
    ipc_stats:          MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"total_instructions,total_cycles,{MetricStats.to_csv_header('ipc')}"
    
    def data_to_csv(self) -> str:
        return f"{self.total_instructions},{self.total_cycles},{self.ipc_stats.data_to_csv()}"

@dataclass
class TaskClockMetric:
    """
    CPU time consumed by the profiled task, measured via perf task-clock events.
    task_clock_total_ms represents the accumulated task-clock time across all iterations.
    """
    task_clock_total_ms: float
    task_clock_stats_ms: MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"task_clock_total_ms,{MetricStats.to_csv_header('task_clock_ms')}"

    def data_to_csv(self) -> str:
        return f"{self.task_clock_total_ms},{self.task_clock_stats_ms.data_to_csv()}"

@dataclass
class L1CacheMetric:
    """
    Private L1 cache localization and data-miss trends.
    """
    l1d_total_accesses:      int
    l1d_total_misses:        int
    l1i_total_accesses:      int
    l1i_total_misses:        int
    l1d_miss_rate_stats_pct: MetricStats
    l1i_miss_rate_stats_pct: MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"l1d_total_accesses,l1d_total_misses,l1i_total_accesses,l1i_total_misses,{MetricStats.to_csv_header('l1d_miss_rate_pct')},{MetricStats.to_csv_header('l1i_miss_rate_pct')}"

    def data_to_csv(self) -> str:
        return f"{self.l1d_total_accesses},{self.l1d_total_misses},{self.l1i_total_accesses},{self.l1i_total_misses},{self.l1d_miss_rate_stats_pct.data_to_csv()},{self.l1i_miss_rate_stats_pct.data_to_csv()}"

@dataclass
class L2CacheMetric:
    """
    Private L2 cache localization and data-miss trends.
    """
    l2_total_accesses:      int
    l2_total_misses:        int
    l2_miss_rate_stats_pct: MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"l2_total_accesses,l2_total_misses,{MetricStats.to_csv_header('l2_miss_rate_pct')}"

    def data_to_csv(self) -> str:
        return f"{self.l2_total_accesses},{self.l2_total_misses},{self.l2_miss_rate_stats_pct.data_to_csv()}"

@dataclass
class LLCacheMetric:
    """
    Last Level Cache (Shared LLC/L3 Cache) system performance footprints.
    """
    llc_total_accesses:      int
    llc_total_misses:        int
    llc_miss_rate_stats_pct: MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"llc_total_accesses,llc_total_misses,{MetricStats.to_csv_header('llc_miss_rate_pct')}"

    def data_to_csv(self) -> str:
        return f"{self.llc_total_accesses},{self.llc_total_misses},{self.llc_miss_rate_stats_pct.data_to_csv()}"

@dataclass
class BranchPredictionMetric:
    """
    Tracks total conditional branches evaluated versus pipeline speculative mispredictions.
    """
    total_branches:      int
    total_branch_misses: int
    branch_miss_rate_stats_pct: MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"total_branches,total_branch_misses,{MetricStats.to_csv_header('branch_miss_rate_pct')}"

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

    @classmethod
    def to_csv_header(cls) -> str:
        return f"{IPCMetric.to_csv_header()},{TaskClockMetric.to_csv_header()},{L1CacheMetric.to_csv_header()},{L2CacheMetric.to_csv_header()},{LLCacheMetric.to_csv_header()},{BranchPredictionMetric.to_csv_header()}"

    def data_to_csv(self) -> str:
        return f"{self.ipc.data_to_csv()},{self.task_clock.data_to_csv()},{self.l1_cache.data_to_csv()},{self.l2_cache.data_to_csv()},{self.llc_cache.data_to_csv()},{self.branch_prediction.data_to_csv()}"

@dataclass
class GPUMetric:
    """
    Accelerated graphics compute block tracked via subprocess background loops using `rocm-smi`.
    """
    activity_stats_pct: MetricStats
    vram_stats_pct:     MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"{MetricStats.to_csv_header('gpu_activity_pct')},{MetricStats.to_csv_header('gpu_vram_pct')}"

    def data_to_csv(self) -> str:
        return f"{self.activity_stats_pct.data_to_csv()},{self.vram_stats_pct.data_to_csv()}"

@dataclass
class MemoryMetric:
    """
    Host volatile workspace allocations sampled via psutil tracking threads.
    """
    total_page_faults:  int
    total_minor_faults: int
    total_major_faults: int
    rss_stats_mb:       MetricStats
    vms_stats_mb:       MetricStats
    page_faults_stats:  MetricStats
    minor_faults_stats: MetricStats
    major_faults_stats: MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"total_page_faults,total_minor_faults,total_major_faults,{MetricStats.to_csv_header('rss_mb')},{MetricStats.to_csv_header('vms_mb')},{MetricStats.to_csv_header('page_faults')},{MetricStats.to_csv_header('minor_faults')},{MetricStats.to_csv_header('major_faults')}"

    def data_to_csv(self) -> str:
        return f"{self.total_page_faults},{self.total_minor_faults},{self.total_major_faults},{self.rss_stats_mb.data_to_csv()},{self.vms_stats_mb.data_to_csv()},{self.page_faults_stats.data_to_csv()},{self.minor_faults_stats.data_to_csv()},{self.major_faults_stats.data_to_csv()}"


@dataclass
class StartupMetric:
    """
    Measures dynamic linker (ld.so) startup overhead captured via LD_DEBUG=statistics.
    Startup time stats represent mean, median, stddev, min, max startup time
    """
    linker_total_cycles:     int
    startup_time_stats_ms: MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"linker_total_cycles,{MetricStats.to_csv_header('startup_time_ms')}"

    def data_to_csv(self) -> str:
        return f"{self.linker_total_cycles},{self.startup_time_stats_ms.data_to_csv()}"

@dataclass
class ThreadMetric:
    total_context_switches:       int
    context_switches_stats:       MetricStats
    thread_count_stats:           MetricStats
    thread_utilization_stats_pct: MetricStats

    @classmethod
    def to_csv_header(cls) -> str:
        return f"total_context_switches,{MetricStats.to_csv_header('context_switches')},{MetricStats.to_csv_header('thread_count')},{MetricStats.to_csv_header('thread_utilization_pct')}"

    def data_to_csv(self) -> str:
        return f"{self.total_context_switches},{self.context_switches_stats.data_to_csv()},{self.thread_count_stats.data_to_csv()},{self.thread_utilization_stats_pct.data_to_csv()}"

@dataclass
class Metrics:
    """The unified mathematical metric encompassing all active profiling vectors."""
    wall_time: WallTimeMetric
    cpu:       CPUMetric     | None
    gpu:       GPUMetric     | None
    memory:    MemoryMetric  | None
    startup:   StartupMetric | None
    thread:    ThreadMetric  | None

    @classmethod
    def to_csv_header(cls) -> str:
        return f"{WallTimeMetric.to_csv_header()},{CPUMetric.to_csv_header()},{GPUMetric.to_csv_header()},{MemoryMetric.to_csv_header()},{StartupMetric.to_csv_header()},{ThreadMetric.to_csv_header()}"

    def data_to_csv(self) -> str:
        return ",".join([
            self.wall_time.data_to_csv(),
            self.cpu.data_to_csv()     if self.cpu     else ",".join([""] * len(CPUMetric.to_csv_header().split(","))),
            self.gpu.data_to_csv()     if self.gpu     else ",".join([""] * len(GPUMetric.to_csv_header().split(","))),
            self.memory.data_to_csv()  if self.memory  else ",".join([""] * len(MemoryMetric.to_csv_header().split(","))),
            self.startup.data_to_csv() if self.startup else ",".join([""] * len(StartupMetric.to_csv_header().split(","))),
            self.thread.data_to_csv()  if self.thread  else ",".join([""] * len(ThreadMetric.to_csv_header().split(",")))
        ])

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

    @classmethod
    def to_csv_header(cls) -> str:
        return f"{Metadata.to_csv_header()},{Workload.to_csv_header()},{Metrics.to_csv_header()}"

    def data_to_csv(self) -> str:
        return f"{self.metadata.data_to_csv()},{self.workload.data_to_csv()},{self.metrics.data_to_csv()}"
