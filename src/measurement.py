from dataclasses import dataclass
import datetime
import platform
import uuid
import psutil
import cpuinfo
import git
import amdsmi

class Version:
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
    def __init__(self):
        try:
            amdsmi.amdsmi_init()
            devices = amdsmi.amdsmi_get_processor_handles()

            if len(devices) > 0:
                info            = amdsmi.amdsmi_get_gpu_asic_info(devices[0])
                mem_info        = amdsmi.amdsmi_get_gpu_vram_usage(devices[0])
                self.model      = info.get('market_name', 'N/A')
                self.target     = info.get('target_graphics_version', 'N/A')
                self.vram_total = mem_info.get('vram_total', 'N/A')
                self.vram_used  = mem_info.get('vram_used', 'N/A')
            else:
                self.model      = "N/A"
                self.target     = "N/A"
                self.vram_total = "N/A"
                self.vram_used  = "N/A"

        except:
            self.model      = "N/A"
            self.target     = "N/A"
            self.vram_total = "N/A"
            self.vram_used  = "N/A"

        finally:
            try:
                amdsmi.amdsmi_shut_down()
            except:
                pass

    def __repr__(self):
        return f"GPUInfo(model='{self.model}', target='{self.target}', vram_total='{self.vram_total}', vram_used='{self.vram_used}')"

class MemoryInfo:
    def __init__(self):
        mem             = psutil.virtual_memory()
        swp             = psutil.swap_memory()
        self.total      = mem.total
        self.available  = mem.available
        self.used       = mem.used
        self.free       = mem.free
        self.swap_total = swp.total
        self.swap_used  = swp.used
        self.swap_free  = swp.free
    
    def __repr__(self):
        return f"MemoryInfo(total={self.total}, available={self.available}, used={self.used}, free={self.free}, swap_total={self.swap_total}, swap_used={self.swap_used}, swap_free={self.swap_free})"

class HardwareInfo:
    def __init__(self):
        self.cpu    = CPUInfo()
        self.gpu    = GPUInfo()
        self.memory = MemoryInfo()

    def __repr__(self):
        return f"HardwareInfo(cpu={self.cpu}, gpu={self.gpu}, memory={self.memory})"

class Metadata:
    def __init__(self, run_id: uuid.UUID):
        self.run_id    = run_id
        self.timestamp = datetime.datetime.now().isoformat()
        self.version   = Version()
        self.software  = SoftwareInfo()
        self.hardware  = HardwareInfo()

    def __repr__(self):
        return f"Metadata(run_id='{self.run_id}', timestamp='{self.timestamp}', version={self.version}, software={self.software}, hardware={self.hardware})"

class Workload:
    def __init__(self, name: str, arguments: list[str], iteration: int):
        self.name      = name
        self.arguments = arguments
        self.iteration = iteration

    def __repr__(self):
        return f"Workload(name='{self.name}', arguments={self.arguments}, iteration={self.iteration})"

@dataclass
class MetricStats:
    mean_value:   float
    median_value: float
    stddev_value: float
    min_value:    float
    max_value:    float

@dataclass
class WallTimeMetric:
    total_ms:        float
    wall_time_stats: MetricStats

@dataclass
class IPCMetric:
    total_instructions: int
    total_cycles:       int
    total_ipc:          float
    ipc_stats:          MetricStats

@dataclass
class L1CacheMetric:
    total_accesses:     int
    total_misses:       int
    total_miss_rate:    float
    l1_miss_rate_stats: MetricStats

@dataclass
class L2CacheMetric:
    total_accesses:     int
    total_misses:       int
    total_miss_rate:    float
    l2_miss_rate_stats: MetricStats

@dataclass
class LLCacheMetric:
    total_accesses:   int
    total_misses:     int
    total_miss_rate:  float
    llc_miss_rate_stats: MetricStats

@dataclass
class BranchPredictionMetric:
    total_branches:          int
    total_branch_misses:     int
    total_branch_miss_rate:  float
    branch_miss_rate_stats:  MetricStats

@dataclass
class CPUMetric:
    ipc:               IPCMetric
    l1_cache:          L1CacheMetric
    l2_cache:          L2CacheMetric
    llc_cache:         LLCacheMetric
    branch_prediction: BranchPredictionMetric

@dataclass
class GPUMetric:
    gpu_utilization: float
    vram_utilization: float

@dataclass
class MemoryMetric:
    mem_stats:  MetricStats
    swap_stats: MetricStats

@dataclass
class SystemMetric:
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
    wall_time: WallTimeMetric
    cpu:       CPUMetric
    gpu:       GPUMetric
    memory:    MemoryMetric
    system:    SystemMetric

class Measurement:
    def __init__(self, metadata: Metadata, workload: Workload, metrics: Metrics):
        self.metadata = metadata
        self.workload = workload
        self.metrics  = metrics
    
    def __repr__(self):
        return f"Measurement(metadata={self.metadata}, workload={self.workload}, metrics={self.metrics})"
