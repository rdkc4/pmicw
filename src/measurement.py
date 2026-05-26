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
    
class WallTimeMetric:
    def __init__(self, mean_ms: float, median_ms: float, stddev_ms: float, min_ms: float, max_ms: float):
        self.mean_ms   = mean_ms
        self.median_ms = median_ms
        self.stddev_ms = stddev_ms
        self.min_ms    = min_ms
        self.max_ms    = max_ms

    def __repr__(self):
        return f"WallTimeMetric(mean_ms={self.mean_ms}, median_ms={self.median_ms}, stddev_ms={self.stddev_ms}, min_ms={self.min_ms}, max_ms={self.max_ms})"

class L1CacheMetric:
    def __init__(self, total_accesses: int, total_misses: int, miss_rate: float):
        self.total_accesses = total_accesses
        self.total_misses   = total_misses
        self.miss_rate      = miss_rate
    
    def __repr__(self):
        return f"L1CacheMetric(total_accesses={self.total_accesses}, total_misses={self.total_misses}, miss_rate={self.miss_rate})"

class L2CacheMetric:
    def __init__(self, total_accesses: int, total_misses: int, miss_rate: float):
        self.total_accesses = total_accesses
        self.total_misses   = total_misses
        self.miss_rate      = miss_rate

    def __repr__(self):
        return f"L2CacheMetric(total_accesses={self.total_accesses}, total_misses={self.total_misses}, miss_rate={self.miss_rate})"

class L3CacheMetric:
    def __init__(self, total_accesses: int, total_misses: int, miss_rate: float):
        self.total_accesses = total_accesses
        self.total_misses   = total_misses
        self.miss_rate      = miss_rate

    def __repr__(self):
        return f"L3CacheMetric(total_accesses={self.total_accesses}, total_misses={self.total_misses}, miss_rate={self.miss_rate})"


class BranchPredictionMetric:
    def __init__(self, total_branches: int, mispredicted_branches: int, misprediction_rate: float):
        self.total_branches        = total_branches
        self.mispredicted_branches = mispredicted_branches
        self.misprediction_rate    = misprediction_rate

    def __repr__(self):
        return f"BranchPredictionMetric(total_branches={self.total_branches}, mispredicted_branches={self.mispredicted_branches}, misprediction_rate={self.misprediction_rate})"

class CPUMetric:
    def __init__(
        self, 
        l1_cache:          L1CacheMetric, 
        l2_cache:          L2CacheMetric, 
        l3_cache:          L3CacheMetric, 
        branch_prediction: BranchPredictionMetric
    ):
        self.l1_cache          = l1_cache
        self.l2_cache          = l2_cache
        self.l3_cache          = l3_cache
        self.branch_prediction = branch_prediction

    def __repr__(self):
        return f"CPUMetric(l1_cache={self.l1_cache}, l2_cache={self.l2_cache}, l3_cache={self.l3_cache}, branch_prediction={self.branch_prediction})"

class GPUMetric:
    def __init__(self):
        self.utilization = "N/A"
        self.memory_usage = "N/A"
    
    def __repr__(self):
        return f"GPUMetric(utilization='{self.utilization}', memory_usage='{self.memory_usage}')"

class MemoryMetric:
    def __init__(
        self, 
        mean_mem_usage_mb: float, 
        min_mem_usage_mb:  float,
        max_mem_usage_mb:  float,
        mean_swp_usage_mb: float,
        min_swp_usage_mb:  float,
        max_swp_usage_mb:  float
    ):
        self.mean_usage_mb     = mean_mem_usage_mb
        self.min_usage_mb      = min_mem_usage_mb
        self.max_usage_mb      = max_mem_usage_mb
        self.mean_swp_usage_mb = mean_swp_usage_mb
        self.min_swp_usage_mb  = min_swp_usage_mb
        self.max_swp_usage_mb  = max_swp_usage_mb

    def __repr__(self):
        return f"MemoryMetric(mean_usage_mb={self.mean_usage_mb}, min_usage_mb={self.min_usage_mb}, max_usage_mb={self.max_usage_mb}, mean_swp_usage_mb={self.mean_swp_usage_mb}, min_swp_usage_mb={self.min_swp_usage_mb}, max_swp_usage_mb={self.max_swp_usage_mb})"

class SystemMetric:
    def __init__(self, page_faults: int, context_switches: int):
        self.page_faults      = page_faults
        self.context_switches = context_switches

    def __repr__(self):
        return f"SystemMetric(page_faults={self.page_faults}, context_switches={self.context_switches})"

class Metrics:
    def __init__(self, wall_time: WallTimeMetric, cpu: CPUMetric, gpu: GPUMetric, memory: MemoryMetric, system: SystemMetric):
        self.wall_time = wall_time
        self.cpu       = cpu
        self.gpu       = gpu
        self.memory    = memory
        self.system    = system
    
    def __repr__(self):
        return f"Metrics(wall_time={self.wall_time}, cpu={self.cpu}, gpu={self.gpu}, memory={self.memory}, system={self.system})"

class Measurement:
    def __init__(self, metadata: Metadata, workload: Workload, metrics: Metrics):
        self.metadata = metadata
        self.workload = workload
        self.metrics  = metrics
    
    def __repr__(self):
        return f"Measurement(metadata={self.metadata}, workload={self.workload}, metrics={self.metrics})"
